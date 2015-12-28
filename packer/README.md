# Packer Build Templates and scripts

These scripts and templates are for [packer](https://www.packer.io), and expect
it to be be installed locally. If you don't, you can install it on a Mac using
homebrew:

    brew install packer

or retrieving it from the download available at https://www.packer.io/downloads.html

## To build locally

    packer build -only=virtualbox-iso template.json
    packer push -name=$ATLAS_USERNAME/rackhd template.json

## To build with ATLAS

Set up your ATLAS_USERNAME and ATLAS_TOKEN environment variables
with your username and API access token from Atlas, then invoke:

    packer push -name=$ATLAS_USERNAME/rackhd template.json

### License notes

These scripts and templates are under an MPL-2.0 license due to leveraging
the content from https://github.com/hashicorp/atlas-packer-vagrant-tutorial.
To abide by the provided license, all files in this directory are shared
under the MPL-2.0 license, as described in the provided LICENSE file
