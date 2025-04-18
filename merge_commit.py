    def merge_commit(self, commit):
        """Merge a specific commit from parent repo into fork"""
        if not self.current_fork:
            messagebox.showerror("Error", "No fork selected")
            return
        
        # Confirm the merge
        if not messagebox.askyesno(
            "Confirm Merge",
            f"Are you sure you want to merge commit {commit.sha[:7]} into your fork?"
        ):
            return
        
        # Use our enhanced merge manager
        repo_name = self.current_fork.full_name
        branch_name = self.current_branch
        commit_sha = commit.sha
        
        def perform_merge():
            return self.merge_manager.merge_commit(
                repo_name, branch_name, commit_sha,
                merge_strategy="merge",
                message=f"Merge commit {commit_sha[:7]} from parent"
            )
        
        self.run_in_thread(
            perform_merge,
            message=f"Merging commit {commit.sha[:7]}...",
            success_message=f"Successfully merged commit {commit.sha[:7]}"
        )
        
        # Refresh the UI after merge
        self.root.after(1000, lambda: self.after_merge())
