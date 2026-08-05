# Job Orchestration System
## Data Monitoring/ Quality Testing

Quality monitoring tasks are used to automatically check existing HydroServer datastreams for values that may be unusual, incorrect, or outside an expected range. These tasks do not create a new datastream. Instead, they monitor selected datastreams and notifies users when a quality rule is triggered.

To create a quality monitoring task, go to the **Quality** section in the Job Orchestration System and click **Add quality task**.

<img src="/job-orchestration/quality_1_click_quality.png" alt="Open the Quality section and add a quality monitoring task" width="550">

Here, enter a clear task name and description so users can understand what the task is checking. In this example, the task is named `Checking range of discharge`, and it is used to monitor the daily average discharge values for the `BC_CONF_A` site. A notification recipient is also added so HydroServer can send an alert if the rule is triggered.

<img src="/job-orchestration/quality_2_create_quality_task.png" alt="Create a quality monitoring task with a range rule for discharge" width="550">

Next, configure the schedule for the task. In this example, the task is set to run every `1 Hour`, starting on `06/25/2026 at 06:43 PM` in the `America/Denver` time zone. The schedule controls how often HydroServer checks the selected datastream for values that do not meet the quality rule.

Under **Quality Rules**, select the datastream that should be monitored. In this example, the rule is applied to `Discharge at BC_CONF_A with average daily discharge`. The rule type is set to `Range` because the goal is to check whether discharge values stay within an expected range. The rule type can also be changed using the dropdown menu depending on the type of quality check needed. Here, the minimum value is set to `0` and the maximum value is set to `50`, so any value below `0` or above `50` will be flagged for review. After all settings are complete, click **Create quality task**.
