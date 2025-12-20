# User Files

When your add-on needs configuration data other than simple keys and values, it can use a special folder called user_files in the root of your add-on’s folder. Any files placed in this folder will be preserved when the add-on is upgraded. All other files in the add-on folder are removed on upgrade.

To ensure the user_files folder is created for the user, you can put a README.txt or similar file inside it before zipping up your add-on.

When Anki upgrades an add-on, it will ignore any files in the .zip that already exist in the user_files folder.

[[source](https://addon-docs.ankiweb.net/addon-config.html#user-files)]
