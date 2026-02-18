# MacroClicker
Macro Tool & Autoclicker By TehWalrusCode

# What is?
I made this program because I was sick of tedious tasks and wanted to automate them for myself.

# What do?
## This software is separated into two different functions. A Macro tool, and an Autoclicker.

## Using the Macro tool
To use the macro tool, first press Record or use the specified hotkey.
Then record the actions you want to repeat, such as mouse clicks, movement, or keyboard presses.
Once you are done, simply press stop or use the same hotkey as record and the actions will appear on screen.
Then all you need to do is hit Play and watch the program replicate those actions exactly
If you want to clear the actions, press the clear button or navigate to File->New
To loop the actions continuously, simply toggle loop and the actions will repeat until stopped by you.
If you wish to save a macro for later use, navigate to File->Save and give your macro a name.
Loading a macro is much the same, simply navigate to File->Load and choose your specific file.
The default directory for macro saves is /macros/

## Using the Autoclicker
To use the autoclicker, first specify your options as follows:

### Click Interval
This is how long the program will wait before clicking the mouse, translated into seconds
1 hour: 3600 seconds
1 minute: 60 seconds
1 second: 1 seconds
1 millisecond: 0.001 seconds
(e.g 1h, 1m, 1s, 100ms translates to one click every 3661.1 seconds)

### Mouse Button
Which button should be pressed: Left, Middle, or Right click

### Click Type
Should it be a single, or double click

### Repeat
Repeat indefinitely, or by number of times

### Cursor Position
Current Location of the mouse, or specific X, Y coordinates

Finally, once you're satisfied, simply press Start or use the hotkey and your mouse will begin clicking immediately.

## Editing Hotkeys
To edit the hotkeys, simply navigate to Edit->Hotkeys and a new window will pop up, allowing you to change any hotkey into a different key if you wish.
It should go without saying that if you use a specific hotkey that you may want to use in a macro, it's probably not going to work like you want it to.
(Warning: You can set the same key for two or more different hotkeys, which will mess up the program.)
You can also change the hotkeys by opening the hotkeys.json file and manually editing them there.

