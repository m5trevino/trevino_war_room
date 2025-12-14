#!/bin/bash

echo -e "\n\033[1;93m[⚡ CLEANUP]\033[0m \033[1;37mPURGING ARTIFACTS FROM GIT INDEX...\033[0m"

# 1. Unstage everything (Keep files on disk, remove from git tracking)
git rm -r --cached . > /dev/null 2>&1

# 2. Re-add everything (Respecting the new .gitignore)
git add .

# 3. Check status
echo -e "\033[0;90mThe following files are staged for the clean repo:\033[0m"
git status -s

# 4. Commit and Push
echo -e "\n\033[1;92m[⚡ GITHUB]\033[0m \033[1;37mPUSHING CLEAN STATE...\033[0m"
git commit -m "REPO CLEANUP: Removed .venv, artifacts, and sensitive data."
git push origin master

echo -e "\n\033[1;92m[⚡ DONE]\033[0m \033[1;37mREPOSITORY SANITIZED.\033[0m"
