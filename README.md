<p align="center">
    <img src="https://user-images.githubusercontent.com/12875506/85908858-c637a100-b7cb-11ea-8ab3-75c0c0ddf756.png" alt="SeedSyncarr" />
</p>

> **Note**: This is a maintained fork of [ipsingh06/seedsyncarr](https://github.com/ipsingh06/seedsyncarr).

<p align="center">
  <a href="https://github.com/thejuran/seedsyncarr">
    <img src="https://img.shields.io/github/stars/thejuran/seedsyncarr" alt="Stars">
  </a>
  <a href="https://ghcr.io/thejuran/seedsyncarr">
    <img src="https://img.shields.io/badge/ghcr.io-thejuran%2Fseedsyncarr-blue" alt="GHCR">
  </a>
  <a href="https://github.com/thejuran/seedsyncarr/blob/master/LICENSE.txt">
    <img src="https://img.shields.io/github/license/thejuran/seedsyncarr" alt="License">
  </a>
</p>

SeedSyncarr is a tool to sync the files on a remote Linux server (like your seedbox, for example).
It uses LFTP to transfer files fast!

## Features

* Built on top of [LFTP](http://lftp.tech/), the fastest file transfer program ever
* Web UI - track and control your transfers from anywhere
* Automatically extract your files after sync
* Auto-Queue - only sync the files you want based on pattern matching
* Delete local and remote files easily
* Fully open source!

## How it works

Install SeedSyncarr on a local machine.
SeedSyncarr will connect to your remote server and sync files to the local machine as
they become available.

You don't need to install anything on the remote server.
All you need are the SSH credentials for the remote server.

## Supported Platforms

* Linux (amd64 and arm64)
* Raspberry Pi (v3, v4, v5)
* Windows (via Docker)
* macOS (via Docker)


## Installation and Usage

Please refer to the [documentation](https://thejuran.github.io/seedsyncarr/).


## Report an Issue

Please report any issues on the [issues](../../issues) page.
Please post the logs as well. The logs are available at:
* Deb install: `<user home directory>/.seedsyncarr/log/seedsyncarr.log`
* Docker: Run `docker logs <container id>`


## Contribute

Contributions to SeedSyncarr are welcome!
Please take a look at the [Developer Readme](doc/DeveloperReadme.md) for instructions
on environment setup and the build process.


## License

SeedSyncarr is distributed under Apache License Version 2.0.
See [License.txt](https://github.com/thejuran/seedsyncarr/blob/master/LICENSE.txt) for more information.



## Screenshots

### Dashboard
![SeedSyncarr Dashboard](doc/images/screenshot-dashboard.png)

### Settings
![SeedSyncarr Settings](doc/images/screenshot-settings.png)
