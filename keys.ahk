;
; AutoHotkey Version: 1.x
; Language:       English
; Platform:       Win9x/NT
; Author:         A.N.Other <myemail@nowhere.com>
;
; Script Function:
;	Template script (you can customize this template by editing "ShellNew\Template.ahk" in your Windows folder)
;

#NoEnv  ; Recommended for performance and compatibility with future AutoHotkey releases.
SendMode Input  ; Recommended for new scripts due to its superior speed and reliability.
SetWorkingDir %A_ScriptDir%  ; Ensures a consistent starting directory.

^!F6:: RunWait, C:\Python27\python.exe interface.py meta
^!F7:: RunWait, C:\Python27\python.exe interface.py lin
^!F8:: RunWait, C:\Python27\python.exe interface.py
^!F9:: RunWait, C:\Python27\python.exe interface.py upkeep
^!F10:: RunWait, C:\Python27\python.exe interface.py vr
^!F11:: RunWait, C:\Python27\python.exe interface.py vistatek
^!F12:: RunWait, C:\Python27\python.exe interface.py addepar