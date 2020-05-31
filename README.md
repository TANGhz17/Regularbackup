# Regularbackup
A regular backup plugin based on [MCDReforged](https://github.com/Fallen-Breath/MCDReforged)

[Here](https://github.com/MCDReforged-Plugins/PluginCatalogue) is a MCDR plugin collection repository

[configure.py](https://github.com/TANGhz17/Regularbackup/blob/master/configure.py)和[requirement.txt](https://github.com/TANGhz17/Regularbackup/blob/master/requirement.txt)暂时不能用

```
MCDReforged/
├─ plugins/
│  ├─ Regularbackup.py
│  ├─ my_plugin1.py
│  └─ ...
│
├─ rb_temp/
│  ├─ Backup_file/
|  |  ├─ time1.zip
|  |  ├─ time2.zip
│  |  └─ ...
│  ├─ temp1/
│  └─ temp2/
│
└─ MCDReforged.py
```

# Environment
Python version needs to be Python 3.8+ & MCDReforged 0.8.2-alpha.Tested on Windows 10 18362 x64 + Python 3.7.4 + MCDRegorged 0.9.2-alpha.

# Usage
1. Download the latest MCDR release in the [release page](https://github.com/Fallen-Breath/MCDReforged/releases). Of course you can just clone this repository to get the latest build (might be unstable but with latest features)
2. Copy `Regularbackup.py` to mcdr_root/plugins
3. Enter `!!MCDR plugin load Regularbackup`
4. Enjoy

# Commands
`!!rb` Show Help Messages

`!!rb make` Make a backup immediatly

`!!rb start <time>` Make a backup every `<time>` minutes

`!!rb status` Show the status of Regular Backup

`!!rb stop` Stop auto backup

# Constant explain
* Please reference [QuickbackupM](https://github.com/TISUnion/QuickBackupM) and [MCDR-AutoCleaner](https://github.com/Forgot-Dream/MCDR-AutoCleaner)
