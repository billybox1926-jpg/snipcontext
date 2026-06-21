@echo off
REM snipcontext.cmd — Windows wrapper to avoid sc.exe shadowing
REM Delegates to the installed snipcontext package, forwarding all arguments.

setlocal

where python >nul 2>&1
if errorlevel 1 (
    where python3 >nul 2>&1
    if errorlevel 1 (
        echo Error: python is not on PATH. 1>&2
        exit /b 1
    )
    python3 -m snipcontext %*
) else (
    python -m snipcontext %*
)

endlocal
