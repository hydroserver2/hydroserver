# Account Management API

The purpose of this API is to extend the [SensorThings standard](/guide/sensor-things.md) with user authentication. This includes creating a new account, retrieving information for a user, and JWT and OAuth authentication endpoints.

Head over to the following page for the list of endpoints:

https://beta.hydroserver2.org/api/account/docs

Note: all these endpoints are available through the HydroServer web application.

::: warning
It's worth noting when creating a new account there's no way to create a private account. This means whatever email, address, phone number, etc. you provide will be available to anyone with access to the database instance. Make sure you provide only the information you're okay with being shared with all users of the system.
:::
