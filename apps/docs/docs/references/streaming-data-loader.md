# HydroServer Streaming Data Loader

You can download the SDL from this page:

https://github.com/hydroserver2/streaming-data-loader/releases

## About

This small desktop app is used to run scheduled ETL (Extract, Transform, Load) jobs to transfer data into HydroServer from local time series data files (such as CSV datalogger output files). The app contains a user interface for authenticating with HydroServer as well as a log file for viewing job runs.

## Installation

### macOS

1. **Mount the Image:** Double-click the downloaded `.dmg` file to open the disk image.
2. **Install:** Drag the **Streaming Data Loader** icon into your **Applications** folder.
3. **Security Authorization:** Because this is a standalone build, macOS may block the initial launch. To allow the app:
   * Open **System Settings** > **Privacy & Security**.
   * Scroll down to the **Security** section.
   * Click **Open Anyway** next to the notice regarding the application.
4. **Launch:** You can now open the app directly from your Applications folder.

### Windows
1. **Extract Files:** Right-click the downloaded `.zip` file and select **Extract All...**. Choose a folder where you would like the application to reside.
2. **Launch:** Navigate to the extracted folder and double-click the **Streaming Data Loader.exe** file.
3. **SmartScreen Bypass:** If you see a "Windows protected your PC" message:
   * Click **More info**.
   * Click **Run anyway**.
4. **Optional:** Right-click the executable and select **Pin to Taskbar** for easier access later.

### Linux (Ubuntu)
1. **Extract:** Unzip the archive to your preferred location.
2. **Set Permissions:** Open a terminal in that folder and run the following command to make the file executable:
   `chmod +x "Streaming Data Loader"`
3. **Launch:** Double-click the executable or run it from the terminal using `./"Streaming Data Loader"`.

