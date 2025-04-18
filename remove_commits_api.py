    def _remove_commits_api_method(self, repo_name, branch_name, commits_to_remove):
        """Remove commits using the GitHub API method with enhanced error handling and performance"""
        logger.info(f"Using enhanced GitHub API method to remove {len(commits_to_remove)} commits")
        
        repo = self.g.get_repo(repo_name)
        
        # Create a temporary branch for the operation
        temp_branch_name = f"temp-remove-commits-{int(datetime.datetime.now().timestamp())}"
        logger.info(f"Creating temporary branch: {temp_branch_name}")
        
        # Get the current branch reference
        branch_ref = repo.get_git_ref(f"heads/{branch_name}")
        
        try:
            # Create the temporary branch
            temp_ref = repo.create_git_ref(f"refs/heads/{temp_branch_name}", branch_ref.object.sha)
            
            # Get all commits in chronological order
            logger.info(f"Fetching all commits from {branch_name}")
            all_commits = list(repo.get_commits(sha=branch_name))
            
            # Filter out selected commits to remove
            commits_to_keep = [c for c in all_commits if c.sha not in commits_to_remove]
            
            if not commits_to_keep:
                raise Exception("Cannot remove all commits from the branch")
                
            # Find the oldest commit to keep
            base_commit = commits_to_keep[-1]
            logger.info(f"Base commit for new history: {base_commit.sha[:7]}")
            
            # Process commits in batches for better performance
            batch_size = 20
            total_commits = len(commits_to_keep)
            
            # Hard reset to the base commit
            temp_ref.edit(base_commit.sha, force=True)
            
            # Apply the commits to keep in batches
            for i in range(0, total_commits - 1, batch_size):
                batch = commits_to_keep[i:i+batch_size]
                logger.info(f"Processing batch {i//batch_size + 1} of {(total_commits + batch_size - 1)//batch_size}")
                
                for commit in reversed(batch):
                    if commit.sha == base_commit.sha:
                        continue
                    
                    # Cherry-pick each commit
                    try:
                        repo.merge(temp_branch_name, commit.sha, f"Cherry-pick {commit.sha[:7]}")
                    except Exception as e:
                        logger.warning(f"Failed to cherry-pick commit {commit.sha[:7]}: {str(e)}")
                        # Try to continue with the next commit
            
            # Update the original branch to point to the new history
            logger.info(f"Updating {branch_name} to new history")
            branch_ref.edit(temp_ref.object.sha, force=True)
            
            # Clean up the temporary branch
            logger.info(f"Cleaning up temporary branch")
            repo.get_git_ref(f"heads/{temp_branch_name}").delete()
            
            return True
        except Exception as e:
            # Clean up the temporary branch in case of error
            try:
                repo.get_git_ref(f"heads/{temp_branch_name}").delete()
            except:
                pass
            raise e
