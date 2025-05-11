# DJGaro

Minimalistic discord bot that streams audio/music. This bot is meant to be **self-hosted**(runs on your local machine) and currently only supports streaming from youtube.

# Requirements

This guide assumes you have python 3.10 or above installed on your machine. If not, search for videos or articles on how to install python on your OS, there are plenty. Also, it's assumed you know the basics of using console/terminals and basic steps such as navigation through directories with the `cd` command.


# Installation and configuration

Since the bot uses APIs from youtube and discord, the user needs to register the bot on discord and youtube in order to get the necessary API keys which are needed for the bot to function. These steps are described below.

## Step 1: Creating new python virtual environment

1) Choose a destination folder/directory where the code will be downloaded. Name it however you want and from now on, in this guide it will be referenced as a `project_dir`.
2) Now, download the bot's code, extract it if it's compressed and place the code folder/directory inside the `project_dir`.
3) The next step is to create a python virtual environment inside the `project_dir`. Open a console/terminal and navigate to the `project_dir` directory. Once in the `project_dir`, execute the following command:
	* For Windows: `py -m venv virtenv`
	* For Linux/MacOS: `python3 -m venv virtenv`
4) The commands above create a virtual environment inside the `project_dir` named `virtenv`. Next, follow the steps below for registering the bot on discord and getting a google/youtube API key.

Your `project_dir` structure should look something like this:

```
project_dir
  |__DJGaro
  |__virtenv
```

## Step 2: Registering the bot on discord

1) First, visit the discord web site and log in with your account.
2) Then visit the developer's section: https://discord.com/developers/applications
3) On the left side-bar, go to "Applications". This will show the registered discord applications(bots) for your account. If you haven't created any applications, then none will be shown.
4) On the right side, click on "New Application" button. A pop-up dialog will appear, prompting you to enter the name for the appilcaton. The name you will enter will be the name of the bot in discord. After the name is provided, click on "Create".
5) After the application is created, discord will redirect to the settings page for the newly created app, if not click on the newly created app.
6) Then, on the left side-bar there will be settings for configuring your newly created app. Naviage to the "Bot" section. Then under the heading "TOKEN" click "Reset Token". This might prompt you to enter your password to confirm it's you. After confirmation a long scrumbled string will be shown. This is the **api key/token that discord gives you and only shows you this one time. You must keep this key private and don't tell or show it to anyone.**
7) Next, open the `.env` file located inside `project_dir/DJGaro/djgaro`. **Copy the token that discord provided and replace the string** `<REPLACE THIS WITH YOUR DISCORD BOT KEY>` **with the discord token inside the** `.env` **file**.
8) Don't forget to save the file. If for any reason you lose the token(key), a new token needs to be created.
9) Next, under the "Privileged Gateway Intents" turn on the "PRESENCE INTENT", "SERVER MEMBERS INTENT" and "MESSAGE CONTENT INTENT".
10) After that, go to the "OAuth2" section on the left side-bar, under the "OAuth2 URL Generator" select the `bot` option, then under the "BOT PERMISSIONS" you need to allow certain permisions. The easiest is to select the `Administrator` permissions which grants all permissions, but since not all permissions are needed for the bot to function, at least you need to allow the following permissions: `View Channels`, `Send Messages`, `Send Messages in Threads`, `Embed Links`, `Read Message History`, `Add Reactions`, `Use Slash Commands`, `Connect`, `Speak`, `Use Voice Activity`, `Use Soundboard` and `Use External Sounds`.
11) Copy the link that appears under the selected permissions and paste it in the web browser. This link is used to invite the bot. Select the server you want and invite the bot. The bot is now a member of the server.

If you have trouble following the steps, visit [this video](https://youtu.be/CHbN_gB30Tw?t=81) and watch it till the 7 minute mark.

## Setep 3: Getting API key from google/youtube

The steps in this section are quite similar to registering the bot on discord. You must have google account registered. If you already have a project on google cloud, then you can use that API key instead of creating new project.

1) Log in to youtube/google with your account.
2) Go to https://console.cloud.google.com/
3) In the upper left corner, there will be the "Google Cloud" logo and next to it there should be a drop-down menu "Select a project". Click on the menu, a pop-up dialog will appear. On the top right side there will be button "New Project". Click on "New Proejct". Then you will need to enter a name for your project. This name doesn't matter much, you only need this project so you can get an API key from google/youtube.
4) After the project is created, navigate to the "APIs and services" section which should be shown below the "Quick access" header. If you can't find it, go to https://console.cloud.google.com/apis/dashboard.
5) At the top of the page near the "Google Cloud" logo make sure your newly created project is selected. Then on the left side-bar navigate to the setting named "Credentials". A new main page wil be shown. On the top of the page click on "Create credentials" and select "API key". A dialog will pop-up with your **api key.** **Similar to the discord api key, you should keep the key private and the key will be shown only this time. If you lose it, you need to get a new key**.
6) Open the same `.env` file where you pasted the discord key and replace the `<REPLACE THIS WITH YOUR YOUTUBE API KEY>` text with your google/youtube api key.
7) Again, don't forget to save the `.env` file with your keys.

If you have trouble following the steps, visit [this video](https://www.youtube.com/watch?v=brCkpzAD0gc). Note that in the video, an API key is generated using an exiting project and not creating a new one.

## Step 4: Installing and running the bot

1) Before installing the Bot, the python virtual environment must be activated. Naviagte to the `project_dir` using a console/powershell, then:
	* For Windows run the following commands:
		* `Set-ExecutionPolicy RemoteSigned` -> this allows you to activate the python virtual environment
		* `.\virtenv\Scripts\activate` -> this command activates the environment
	* For Linux/MacOS:
		* `source ./virtenv/bin/activate`
2) Now the virtual environment is activated, and the Bot can be installed. First, navigate to the main top directory of the bot `DJGaro` i.e `project_dir/DJGaro/` and run the following command:
	* For Windows: `py -m pip install .`
	* For Linux/MacOS: `python3 -m pip install .`
3) After the installation process is finished, you can run the bot by executing `garo-start` in a console/powershell. For stopping, just press `Ctrl + C` in the same console window, or exit the window.

# Usage and commands

Currently the bot supports commands with the `!` prefix and the following commands are available:
* `!join` -> joins the bot into the current voice channel of the command issuer. If not in voice channel, bot complains.
* `!leave` -> if in voice channel, leaves the channel
* `!play <youtube video url or playlist url or search query` -> plays the audio from the provided resouce if it's a URL. If a search query is provided, the first result from that query is played. This command resets/empties the internal playlist and initializes it with the new provided resource.
* `!pause` -> pauses the currently playing stream, if any
* `!resume` -> resumes the currently playing stream, if any
* `!stop` -> stops the currently playing stream, if any
* `!next` -> plays the next song in the playlist, if any
* `!previous`, `!prev` -> plays the previous song in the playlist, if any
* `!rewind`, -> restarts the currently playing stream
* `!repeat <repeat-mode>` -> sets the repeat mode of the playlist. The `<repeat-mode>` parametar can be one of **all**(default), **one** or **none**.
* `!listsongs`, `!ls` -> lists at most 5 songs around the one that is currently playing
* `!currentsong`, `!cs` -> lists the currently playing song

# Notes

* Since the bot is self-hosted, the quality if the audio stream depends on the internet speed of the host. The bot currently supports streaming only OPUS encoded audio which sacrifices audio quality so the stream doesn't stutter or jitter.
* The initial starting of the audio stream might take a couple of seconds while the bot gathers resources to play the audio. This is also very much dependent on the internet speed of the host. The following streams should be faster because the bot downloads the necessary resources for the next song in the list.
* Avoid sending `!next` commands too quicky, since the bot needs time to download the resources.
* Currently the maximum number of songs in a playlist is 50. This will be changed once additional commands for adding items in a existing playlist become available.
