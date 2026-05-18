# Monitoring Sites

A monitoring "site" refers to a single location where observations are recorded or created. This could be a collection of sensors grouped together like a weather station measuring temperature, wind speed, and atmospheric pressure. Or, it could simply be a lab worker going out to the same place in a river and measuring the water level. Typically, this is a fixed physical location where one or more instruments are deployed for making measurements.

A site encompasses both the physical location and the metadata describing the site such as site name, site code, any photos of the site, and a key:value tagging system to help you describe that location beyond what's available in the fields provided by the data model and API.

A site is _not_ the physical sensors or instruments that are deployed at the site's location. That metadata lives in the Sensor table of HydroServer's database.

::: tip A side note on Thing vs. Site
Given that it is an "Internet of Things" standard, SensorThings uses the term `Thing` in order to stay as general as possible. In the field of water data management, users are more more often familiar with the term `Site` as in a `monitoring site`. Therefore, we've opted to refer to a `Thing` as `Site` in all of our user facing applications. But, to strictly follow the SensorThings specification, we've kept SensorThing's original `Thing` naming in our data model and APIs.
:::

## key:value tagging system

Most of the metadata you will need is already supported by HydroServer’s API. However, for organization-specific or custom information, tags offer a flexible way to store additional metadata that doesn’t fit into the standard fields. Tags are extra, customizable, key:value pairs that provide more context or categorization to the data. For example, you might use tags to link to your sites to 3rd party websites: `website:https://my-website.com`. You can use tags to specify values for additional attributes of a site, or you can point to external websites or URLs where more detailed information about that site might be maintained.
