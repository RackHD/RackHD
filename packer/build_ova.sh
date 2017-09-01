#!/bin/bash
set -x
###################################################
Usage(){
  echo "Function: this script is used to build rackhd ova":
  echo "usage: $0 [arguments]"
  echo "  Mandatory Arguments:"
  echo "    --RACKHD_DIR: The directory of rackhd repo."
  echo "  Optional Arguments:"
  echo "    --OS_VER: The ubuntu iso version for ova build.
                      Default: ubuntu-14.04"
  echo "    --ANSIBLE_PLAYBOOK: Use which playbook to install rackhd and dependency.
                                Default: rackhd_local.yml"
  echo "    --DEBIAN_REPOSITORY: by default is to using RackHD Bintray repo: deb https://dl.bintray.com/rackhd/debian trusty release,
                                 if using latest nightly build, can choose deb https://dl.bintray.com/rackhd/debian trusty main.
                                 and other repo like private artifactory is also ok. just let the /etc/apt/source.list recognize it."
  echo "    --RACKHD_VERSION: The version of rackhd debian package that will be installed into ova.
                              Default: latest."
  echo "    --BUILD_STAGE: Default: BUILD_ALL. other options as below:
                           - BUILD_TEMPLATE (a prebuild cache, vmx or ovf),
                           - BUILD_FINAL ( Build ova or box from the template) , or BUILD_ALL (including both steps)."
  echo "    --CACHE_IMAGE_DIR: The dir stored prebuilt vmx file. Is necessary when BUILD_FINAL"
  echo "    --TARGET_DIR: A dir for storing all the ova build output.
                      default: current dir RackHD/packer"
  echo "    --CI_SIGNING_KEY: The key for encrypting ova."
  echo "    --GPG_SIGNING_KEY: The key for gpg signing."
  echo "    --CUSTOMIZED_PROPERTY_OVA: by default false, only effective when BUILD_TYPE is vmware..
                                       if true, the OVA can be specified IP during deployment. only supported by vCenter"
}

###################################################

INFO_HEADER="[Info]"
WARNING_HEADER="[Warning]"
ERROR_HEADER="[Error]"

# early exit on command failure
set -e

varDefine(){
    VM_NAME=rackhd-${OS_VER}
    BASENAME=${VM_NAME}
    OVA="${BASENAME}.ova"
    # default is output-${type}. you can customized in packer's json by "output_directory" param
    VMDIR=output-vmware-vmx # output of Build VMWare from VMX
}

prepareMaterials(){
    set +e
    pkill packer
    pkill vmware
    set -e
    # Prepare packer and cfg file
    CFG_FILE=template.cfg
    # parameter file pass to packer
    echo {                                                     > $CFG_FILE
    echo  \"playbook\": \"${ANSIBLE_PLAYBOOK}\",              >> $CFG_FILE
    echo  \"vm_name\": \"${VM_NAME}\",                        >> $CFG_FILE
    if [  -n "${DEBIAN_REPOSITORY}" ];  then
         echo  \"deb_repository\": \"${DEBIAN_REPOSITORY}\",  >> $CFG_FILE
    fi
    echo  \"rackhd_version\": \"${RACKHD_VERSION}\"           >> $CFG_FILE
    echo }                                                    >> $CFG_FILE

    PACKER=packer
    if [ -x /opt/packer/packer ]
    then
        PACKER=/opt/packer/packer
    fi

    # Enable Verbose Packer Logging
    # see https://www.packer.io/docs/other/environmental-variables.html for details
    export PACKER_LOG=1
    export PACKER_LOG_PATH=$TARGET_DIR/packer-debug.log
    export PACKER_NO_COLOR=1  # for Jenkins usage. if manual run, suggest to turn color on (set to 0)
    export PACKER_CACHE_DIR=$HOME/.packer_cache

    # Check Free Disk Space,  VMWare Workstation may stuck if disk space too small
    fd_in_kb=$(df  .  | awk '/^\/dev/ {print $4}')
    fd_thres=$(expr 1024 '*' 1024 '*' 8)  # set to 8G as threshold.
    if [ $fd_in_kb -lt  $fd_thres ]
    then
        echo "The Free Up Disk Space($fd_in_kb KB) is not suffcient(recommended to $fd_thres KB). it may cause VMWare Workstation to stuck."
        exit 2
    fi
}

packerBuildOVA(){
    #packer template file
    PACKER_TEMP=template-${OS_VER}.json

    # execute 'packer build'
    if [ "$BUILD_STAGE" == "BUILD_TEMPLATE" ]; then
        #Build from  iso, create a Pre-build Cache ( vmware:iso-->vmx, virtualbox: iso-->ovf )
        $PACKER build --force --only=vmware-iso  --var-file=$CFG_FILE  ${PACKER_TEMP}  | tee $TARGET_DIR/packer-install.log
    else
        if [ "$BUILD_STAGE" == "BUILD_FINAL" ]; then
             #Build from cache template, and output the final image .(vmware: vmx-->ova, virtualbox: ovf-->box)
             mkdir output-vmware-iso && mv $CACHE_IMAGE_DIR/* ./output-vmware-iso
             $PACKER build --force --only=vmware-vmx  --var-file=$CFG_FILE  --var "playbook=${ANSIBLE_PLAYBOOK}" ${PACKER_TEMP}   | tee $TARGET_DIR/packer-install.log
        else
             #Build from scratch, vmware: iso-->vmx-->ova
             $PACKER build --force --only=vmware-iso  --var-file=$CFG_FILE  ${PACKER_TEMP}  | tee $TARGET_DIR/packer-install.log && \
             $PACKER build --force --only=vmware-vmx  --var-file=$CFG_FILE  --var "playbook=${ANSIBLE_PLAYBOOK}" ${PACKER_TEMP}   | tee $TARGET_DIR/packer-install.log
        fi
    fi
    ## Check packer build command status, because above we use pipeline, so use  ${PIPESTATUS[0]} to catch return-code of command before pipeline.(only works on bash)
    if [ ${PIPESTATUS[0]} != 0 ]; then
        echo "${ERROR_HEADER} Packer Build failed.. exit"
        exit 3
    fi
    if  [ "$BUILD_STAGE" == "BUILD_TEMPLATE" ]; then
         echo "{INFO_HEADER} Build VMX is successful... Exit the build_ova Script. Use BUILD_STAGE=BUILD_FINAL and ANSIBLE_PLAYBOOK=rackhd_package_mini env variable to build OVA from this VMX."
    fi
}

postProcess(){
  vmxToOVA
  virusScan
  customizedPropertyOVA
  createChecksum
  gpgSigning
  chmod a=r "$OVA"*
  if [ $TARGET_DIR != `pwd` ]; then
      mv "$OVA"* $TARGET_DIR
  fi
}



vmxToOVA(){
    # Prepare Signing Key (used for Jenkins Build Release)
    if [ -f "$CI_SIGNING_KEY" ]
    then
        SIGN_ARGS="--privateKey=$CI_SIGNING_KEY"
        echo "${INFO_HEADER}Signing the OVA with the CI key"
    else
        echo "${INFO_HEADER}No signing to be performed.. skip."
    fi

    # Conver the VM Disk and VMX folder into an OVA
    ovftool $SIGN_ARGS -o ${VMDIR}/${VM_NAME}.vmx $OVA
    if [ $? != 0 ]; then
        echo "${ERROR_HEADER} ovftool exec failed.. exit"
        exit 4
    fi
}

virusScan(){
    # Do Virus Scan
    if [ -x /usr/bin/clamscan ]
    then
        echo "${INFO_HEADER} Doing ClamScan"
        rm -rf "$OVA.avscan"
        /usr/bin/clamscan --log="$OVA.avscan" --max-filesize=4000M --max-scansize=4000M -r ${VMDIR} --allmatch
    else
        echo "${INFO_HEADER} skip clamscan..."
    fi
}


customizedPropertyOVA(){
  if [ "${CUSTOMIZED_PROPERTY_OVA}" == "true" ];
  then
      bash add_IP_property_to_ova.sh ${OVA}
      if [ $? != 0 ]; then
           echo "${ERROR_HEADER} add_IP_property_to_ova.sh ${OVA} failed! Abort!"
           exit 5
      fi
  fi
}

createChecksum(){
    # Create MD5 & Sha256 checksum file

    rm -f "$OVA.md5" "$OVA.sha"
    md5sum "$OVA" > "$OVA.md5"
    sha256sum  "$OVA" > "$OVA.sha"

    echo "***************************"
    echo "Created : $OVA"
    echo "also find $OVA.md5 & $OVA.sha"
    echo "***************************"
}


gpgSigning(){
  # Do gpg signing
  if [ -f "$GPG_SIGNING_KEY" ]
  then
      export GNUPGHOME=$(mktemp -d)
      trap -- "rm -rf $GNUPGHOME" EXIT
      gpg --allow-secret-key-import --import "$GPG_SIGNING_KEY"
      gpg -k

      rm -rf "$OVA.md5.gpg"
      gpg -a --output "$OVA.md5.gpg" --detach-sig "$OVA.md5"

      rm -rf "$OVA.sha.gpg"
      gpg -a --output "$OVA.sha.gpg" --detach-sig "$OVA.sha"

      if [ -f "$OVA.avscan" ]
      then
          gpg -a --output "$OVA.avscan.gpg" --detach-sig "$OVA.avscan"
      fi
  fi
}

###################################################################
#
#  Parse and check Arguments
#
##################################################################
parseArguments(){
    while [ "$1" != "" ]; do
        case $1 in
            --RACKHD_DIR )                  shift
                                            RACKHD_DIR=$1
                                            ;;
            --OS_VER )                      shift
                                            OS_VER=$1
                                            ;;
            --BUILD_STAGE )                 shift
                                            BUILD_STAGE=$1
                                            ;;
            --CACHE_IMAGE_DIR )             shift
                                            CACHE_IMAGE_DIR=$1
                                            ;;
            --ANSIBLE_PLAYBOOK )            shift
                                            ANSIBLE_PLAYBOOK=$1
                                            ;;
            --RACKHD_VERSION )              shift
                                            RACKHD_VERSION=$1
                                            ;;
            --DEBIAN_REPOSITORY )           shift
                                            DEBIAN_REPOSITORY=$1
                                            ;;
            --TARGET_DIR )                  shift
                                            TARGET_DIR=$1
                                            ;;
            --CI_SIGNING_KEY )              shift
                                            CI_SIGNING_KEY=$1
                                            ;;
            --GPG_SIGNING_KEY )             shift
                                            GPG_SIGNING_KEY=$1
                                            ;;
            --CUSTOMIZED_PROPERTY_OVA )     shift
                                            CUSTOMIZED_PROPERTY_OVA=$1
                                            ;;
            * )                             Usage
                                            exit 1
        esac
        shift
    done

    if [ ! -n "${RACKHD_DIR}" ] ; then
        echo "[Error]Arguments RACKHD_DIR is required!"
        Usage
        exit 1
    fi

    ####  Ubuntu Version  ###
    if  [ ! -n "${OS_VER}" ];  then
        OS_VER=ubuntu-14.04
        echo "${INFO_HEADER} Packer OVA Build based on $OS_VER ( using template-${OS_VER}.json)"
    fi

    # By default. use ansible playbook : rackhd_local.yml
    if  [ ! -n "${ANSIBLE_PLAYBOOK}" ];  then
        ANSIBLE_PLAYBOOK=rackhd_local
    fi
    if [ ! -f "$RACKHD_DIR/packer/ansible/${ANSIBLE_PLAYBOOK}.yml" ]; then
        echo "${ERROR_HEADER} The target ansible playbook($RACKHD_DIR/packer/ansible/${ANSIBLE_PLAYBOOK}.yml) does not exist. Aborting..."
        exit 3
    fi

    ### $RACKHD_VERSION is used for package install provisioner:  `apt-get install rackhd=$RACKHD_VERSION` ###
    if [  -n "${RACKHD_VERSION}" ];  then
       if [ $ANSIBLE_PLAYBOOK != "rackhd_local" ]; then
           echo "${INFO_HEADER} Build VM based on RackHD Debian Package ${RACKHD_VERSION} "
      else
           echo "${WARNING_HEADER} Skip the ENV VAR: RACKHD_VERSION=$RACKHD_VERSION, this variable is useless for rackhd_local.yml (build from src code)".
       fi
    else
       if [ $ANSIBLE_PLAYBOOK != "rackhd_local" ]; then
           echo "${INFO_HEADER} Install RackHD Package without specific version(default latest)."
       fi
    fi

    if [  -n "${DEBIAN_REPOSITORY}" ] && [ $ANSIBLE_PLAYBOOK == "rackhd_local" ]; then
            echo "${WARNING_HEADER} DEBIAN_REPOSITORY variable is useless for rackhd_local.yml (build from src code)".
    fi

    if [ ! -n "${TARGET_DIR}" ] ; then
        TARGET_DIR=$RACKHD_DIR/packer
        echo "[Info] Use default arguments TARGET_DIR: $RACKHD_DIR/packer"
    else
         if [ ! -d "${TARGET_DIR}" ]; then
	           mkdir -p ${TARGET_DIR}
         fi
    fi

    ### For OVA Build, option is to build OVA directlly from VMX, or build a VMX (which includes all RackHD Prerequisite)
    if [ "$BUILD_STAGE" == "BUILD_ALL" ] ; then
        echo "${INFO_HEADER} Full Build:  Install RackHD with (1) ansible playbook rackhd_prepare.yml, (2) ansible playbook ${ANSIBLE_PLAYBOOK}.yml "
    else
        if [ "$BUILD_STAGE" == "BUILD_FINAL" ] ; then
            if [ ! -n "$CACHE_IMAGE_DIR" ];then
                echo "${ERROR_HEADER} CACHE_IMAGE_DIR is necessary for BUILD_FINAL"
            fi
            echo "${INFO_HEADER} Second Half Build: Install RackHD with ansible :  ${ANSIBLE_PLAYBOOK}.yml "
        else
            if [ "$BUILD_STAGE" == "BUILD_TEMPLATE" ] ; then
                echo "${INFO_HEADER} First Half Build: Prepare RackHD dependency with ansible :  rackhd_prepare.yml "
            else
                echo "${ERROR_HEADER} Unrecongnized parameter BUILD_STAGE=$BUILD_STAGE,  Abort ! "
                exit 2
            fi
        fi
    fi

    # By default. disable CUSTOMIZED_PROPERTY_OVA, because only supported by vCenter. not by vSphere
    if  [ ! -n "${CUSTOMIZED_PROPERTY_OVA}" ];  then
        CUSTOMIZED_PROPERTY_OVA=false;
    fi
    if [ "${CUSTOMIZED_PROPERTY_OVA}" == "true" ];
    then
         echo "${INFO_HEADER} the OVA created will carry with customized property, like admin port IP "
    else
         echo "${INFO_HEADER} the OVA created will not carry with customized property."
    fi
}

parseArguments "$@"
cd $RACKHD_DIR/packer
varDefine
prepareMaterials
packerBuildOVA
postProcess
