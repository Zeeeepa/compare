    def remove_selected_commits(self):
        """Remove selected commits from the branch"""
        repo_name = self.commit_list_repo_var.get()
        branch_name = self.commit_list_branch_var.get()
        
        if not repo_name or not branch_name:
            messagebox.showerror("Error", "Please select a repository and branch")
            return
            
        # Get selected commits
        selected_commits = [sha for sha, var in self.commit_checkboxes.items() if var.get()]
        
        if not selected_commits:
            messagebox.showinfo("Information", "No commits selected for removal")
            return
        
        # Confirmation dialog
        response = messagebox.askyesno(
            "Confirm Commit Removal", 
            f"Are you sure you want to remove {len(selected_commits)} selected commits from {branch_name}?\n\n"
            "This operation will rewrite the branch history and cannot be undone."
        )
        
        if not response:
            return
        
        def perform_removal():
            temp_branch_name = None
            try:
                repo = self.g.get_repo(repo_name)
                
                # Get the current branch reference
                try:
                    branch_ref = repo.get_git_ref(f"heads/{branch_name}")
                except GithubException as e:
                    if e.status == 404:
                        raise Exception(f"Branch '{branch_name}' not found")
                    raise Exception(f"Failed to access branch: {str(e)}")
                
                # Create a temporary branch for the operation
                temp_branch_name = f"temp-remove-commits-{int(datetime.datetime.now().timestamp())}"
                try:
                    temp_ref = repo.create_git_ref(f"refs/heads/{temp_branch_name}", branch_ref.object.sha)
                except GithubException as e:
                    raise Exception(f"Failed to create temporary branch: {str(e)}")
                
                # Get all commits in chronological order
                try:
                    all_commits = list(repo.get_commits(sha=branch_name))
                except GithubException as e:
                    raise Exception(f"Failed to fetch commits: {str(e)}")
                
                # Filter out selected commits to remove
                commit_to_keep = [c for c in all_commits if c.sha not in selected_commits]
                
                if not commit_to_keep:
                    raise Exception("Cannot remove all commits from the branch")
                    
                # Find the oldest commit to keep
                base_commit = commit_to_keep[-1]
                
                # Cherry-pick commits to the temporary branch
                # First, hard reset to the base commit
                try:
                    temp_ref.edit(base_commit.sha, force=True)
                except GithubException as e:
                    raise Exception(f"Failed to reset temporary branch: {str(e)}")
                
                # Cherry-pick each commit to keep in reverse order (oldest to newest)
                for i, commit in enumerate(reversed(commit_to_keep[:-1])):  # Skip the base commit
                    try:
                        # Get the commit data
                        commit_data = repo.get_git_commit(commit.sha)
                        tree = commit_data.tree
                        parents = [base_commit.sha]
                        
                        # Handle merge commits
                        if len(commit_data.parents) > 1:
                            # For merge commits, we need to ensure we have the correct parent
                            # Find the parent that's in our keep list
                            valid_parents = [p for p in commit_data.parents if p.sha in [c.sha for c in commit_to_keep]]
                            if valid_parents:
                                parents = [valid_parents[0].sha]
                            else:
                                # Skip this commit if we can't find a valid parent
                                continue
                        
                        # Create a new commit with the same data
                        new_commit = repo.create_git_commit(
                            message=commit_data.message,
                            tree=tree,
                            parents=parents
                        )
                        
                        # Update the temp branch reference
                        temp_ref.edit(new_commit.sha, force=True)
                        
                        # Update the base commit for the next iteration
                        base_commit = repo.get_git_commit(new_commit.sha)
                        
                        # Log progress
                        self.status_var.set(f"Cherry-picking commit {i+1}/{len(commit_to_keep)-1}...")
                        
                    except GithubException as e:
                        raise Exception(f"Failed to cherry-pick commit {commit.sha}: {str(e)}")
                
                # Update the original branch to point to the new history
                try:
                    branch_ref.edit(temp_ref.object.sha, force=True)
                except GithubException as e:
                    raise Exception(f"Failed to update branch: {str(e)}")
                
                # Delete the temporary branch
                try:
                    temp_ref.delete()
                    temp_branch_name = None  # Mark as deleted
                except GithubException as e:
                    # Non-fatal error, just log it
                    print(f"Warning: Failed to delete temporary branch: {str(e)}")
                
                # Update UI in main thread
                self.root.after(0, lambda: self.after_commit_removal(len(selected_commits)))
                
            except Exception as e:
                error_msg = str(e)
                # Clean up temporary branch if it exists
                if temp_branch_name:
                    try:
                        repo.get_git_ref(f"refs/heads/{temp_branch_name}").delete()
                    except:
                        pass  # Ignore cleanup errors
                raise Exception(f"Failed to remove commits: {error_msg}")
        
        # Run in background thread
        self.run_in_thread(perform_removal, 
                        message=f"Removing {len(selected_commits)} commits...", 
                        success_message=f"Successfully removed {len(selected_commits)} commits")
