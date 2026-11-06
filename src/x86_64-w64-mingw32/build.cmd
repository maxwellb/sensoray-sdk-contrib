@echo off
rem Build the Sensoray 2600 Windows port (x86_64-w64-mingw32) using MSYS2 UCRT64.
rem
rem Author   : Maxwell Bloch (github.com/maxwellb)
rem Copyright: (C) 2026 Maxwell Bloch
rem
rem Runs `make` in this directory from an MSYS2 UCRT64 shell. Pass a make target
rem to run a specific target, e.g. `build.cmd clean` or `build.cmd demo`.

setlocal

if not defined MSYS2_ROOT set "MSYS2_ROOT=C:\msys64"
set "MSYS2_SHELL=%MSYS2_ROOT%\msys2_shell.cmd"

if not exist "%MSYS2_SHELL%" (
    echo Error: MSYS2 not found at "%MSYS2_SHELL%".
    echo Install MSYS2, or set MSYS2_ROOT to your installation directory.
    exit /b 1
)

"%MSYS2_SHELL%" -ucrt64 -where "%~dp0" -no-start -defterm -c "make %*"

exit /b %ERRORLEVEL%
