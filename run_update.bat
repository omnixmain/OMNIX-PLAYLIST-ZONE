@echo off
echo Updating Hotstar Playlist...
python scripts/hotstar-jio.py
if %errorlevel% neq 0 (
    echo.
    echo Error: Failed to update playlist.
    pause
    exit /b %errorlevel%
)
echo.
echo Playlist updated successfully!
echo Pushing to GitHub...
git add playlist/hotstar-jio.m3u
git commit -m "Manual playlist update"
git push
echo.
echo Done!
pause
