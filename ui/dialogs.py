"""Dialog wrappers for wxPython."""
import wx


class messagebox:
    """Message box wrapper compatible with Tkinter interface."""
    
    @staticmethod
    def showinfo(title, message):
        """Show info message box.
        
        Args:
            title: Dialog title
            message: Message to display
        """
        wx.MessageBox(message, title, wx.OK | wx.ICON_INFORMATION)
    
    @staticmethod
    def showwarning(title, message):
        """Show warning message box.
        
        Args:
            title: Dialog title
            message: Message to display
        """
        wx.MessageBox(message, title, wx.OK | wx.ICON_WARNING)
    
    @staticmethod
    def showerror(title, message):
        """Show error message box.
        
        Args:
            title: Dialog title
            message: Message to display
        """
        wx.MessageBox(message, title, wx.OK | wx.ICON_ERROR)
    
    @staticmethod
    def askyesno(title, message):
        """Show yes/no question dialog.
        
        Args:
            title: Dialog title
            message: Question to display
        
        Returns:
            True if Yes, False if No
        """
        res = wx.MessageBox(message, title, wx.YES_NO | wx.ICON_WARNING)
        return res == wx.YES


class filedialog:
    """File dialog wrapper compatible with Tkinter interface."""
    
    @staticmethod
    def askopenfilename(title="Select File", filetypes=(("All files", "*.*"),)):
        """Show open file dialog.
        
        Args:
            title: Dialog title
            filetypes: File type filters
        
        Returns:
            Selected file path or empty string
        """
        wildcard = "\n".join([f"{desc}\n{pattern}" for desc, pattern in filetypes])
        dlg = wx.FileDialog(None, title, wildcard=wildcard, style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST)
        if dlg.ShowModal() == wx.ID_OK:
            path = dlg.GetPath()
            dlg.Destroy()
            return path
        dlg.Destroy()
        return ""
    
    @staticmethod
    def askdirectory(title="Select Folder"):
        """Show directory selection dialog.
        
        Args:
            title: Dialog title
        
        Returns:
            Selected directory path or empty string
        """
        dlg = wx.DirDialog(None, title, style=wx.DD_DEFAULT_STYLE | wx.DD_DIR_MUST_EXIST)
        if dlg.ShowModal() == wx.ID_OK:
            path = dlg.GetPath()
            dlg.Destroy()
            return path
        dlg.Destroy()
        return ""
