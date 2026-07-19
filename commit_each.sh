#!/bin/bash
git remote add genius git@github.com:genius-0963/SelfSmart.git || git remote set-url genius git@github.com:genius-0963/SelfSmart.git

BRANCH="auto-update-$(date +%Y%m%d%H%M%S)"
git checkout -b $BRANCH

git status --porcelain | while IFS= read -r line; do
    status=${line:0:2}
    file=${line:3}
    
    # Handle renames "R  old -> new"
    if [[ "$status" == *"R"* ]]; then
        file=$(echo "$file" | awk -F' -> ' '{print $2}')
    fi
    
    # Remove surrounding quotes if any
    file=$(echo "$file" | sed -e 's/^"//' -e 's/"$//')
    
    # Skip empty lines
    if [ -z "$file" ]; then
        continue
    fi
    
    git add "$file"
    git commit -m "Update $file"
done

git push -u genius $BRANCH
