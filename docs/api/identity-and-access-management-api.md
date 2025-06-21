# Identity and Access Management API

This API extends the SensorThings standard with user authentication and access control. This includes managing user accounts, grouping data into access controlled workspaces, and restricting select actions to authorized users.

Authentication is not required for public data access. However, if you require access to restricted data or wish to upload or modify your own data, you will need to authenticate with HydroServer.

Head over to the following page for the list of endpoints:

https://playground.hydroserver.org/api/auth/docs

Note: all these endpoints are available through the HydroServer web application.

::: info Account information is Public
It's worth noting when creating a new account there's no way to create a private account. This means whatever email, address, phone number, etc. you provide will be available to anyone with access to the database instance. Make sure you provide only the information you're okay with being shared with all users of the system.
:::
