# Loading Data from an Internet Connected Datalogger

The HydroServer SensorThings API supports posting Observations data. This means that any device or datalogger that is connected to the Internet and can make HTTP POST requests can stream data directly into HydroServer through the SensorThings API. For generic guidance on using the SensorThings API, see our documentation on [loading data using SensorThings](/user-guides/how-to/loading-data-with-sensorthings.md). In this article, we describe how to write code to send data to HydroServer and provide examples.

## Using a Campbell Scientific Datalogger

Most of the newer Campbell Scientific dataloggers include an `HTTPPost()` function in their CRBasic instruction set. This function is a straightforward way to send HTTP POST requests to a remote server like HydroServer. To use `HTTPPost()`, the datalogger must be connected to the Internet via Wi-Fi or cellular data connection. For more remote stations where Wi-Fi or cellular Internet connections are not possible, you can set up whatever telemetry system you need to retrieve the data from your station using Campbell Scientific's Loggernet software and then load the data from the ".dat" file retrieved to HydroServer using the Streaming Data Loader or HydroServer's Job Orchestration System.

A <a href="/user-guides/how-to/CR350_example.CRB" download>full example program for using a Campbell Scientific CR350 series datalogger</a> to POST data directly to HydroServer is provided here. Below, we describe sections of this program to give you an overview of how it works.

### Setting up Variables and Constants

Your program needs some information up front to enable connecting to HydroServer and to enable construction of the HTTP POST requests you will send. In our example, we set the following:

- `data_string`: This string variable holds the result of getting the latest record from the program's data table using the CRBasic `GetRecord()` function. It must be dimensioned to be large enough to hold that record.
- `post_header`: This is a string variable to hold the header of the HTTP POST request. It must be dimensioned to be long enough to contain the header information.
- `json_string`: This is a string variable that holds the payload of the HTTP POST request. It must be dimensioned to be long enough for the payload you want to send.
- `http_post_tx`: This is a variable to contain the result of calling the CRBasic `HTTPPost()` function.
- `http_response`: This is a string variable to contain the response from the server you send the HTTP POST request to. It must be dimensioned to be large enough to contain the response (especially for debugging purposes).
- `num_datastreams`: The number of datastreams that you are loading data to. This should be the same as the number of variables that you are measuring and recording to the program's data table.
- `result_string`: This is a string array that is used to read the latest record from the program's data table. It needs to be dimensioned to have number of elements = num_datastreams + 1 (the + 1 is the timestamp)
- `datastream_ids`: This is a string array used to contain the UUIDs for the datastreams you are loading data into. You must supply a UUID for each datastream, and they should be specified in the same order as the variables in the program's data table.

### Specifying the Output Data Table

Even though your program will regularly send your data to HydroServer, you should also log the data into the datalogger's local storage to ensure that your data are safely stored in case you lose Internet connectivity or something else goes wrong. You need to define an output data table that contains the values you want to POST to HydroServer. The order of the column definitions should be the same as the order you specified for the datastream UUIDs in the `datastream_ids` array. The data table from the CR350 example looks like the following:

```vb
' Define Data Tables.
DataTable (Output,1,-1)
	DataInterval (0,1,Min,10)
	' Define the Datastreams (columns) to POST to HydroServer in the order to be POSTed
	' The program retrieves the most recent row from the table and POSTs the data
	Minimum (1,Batt_volt,FP2,False,False)
	Average (1,PTemp,FP2,False)
EndTable
```

In this example, the datalogger records the minimum battery voltage and average panel temperature every 1-minute. The scan interval for the example program is 1-second, so one record is written to the table each minute.

### Sending the HTTP POST Request

The actual HTTP POST request is sent via a one line call to the CRBasic `HTTPPost()` function:

```vb
http_post_tx = HTTPPost (SERVER_ADDRESS,json_string,http_response,post_header)
```

The `SERVER_ADDRESS` is the address to the Observations endpoint of the SensorThings API on the HydroServer you are sending data to. We recommend defining `SERVER_ADDRESS` as a constant value at the beginning of your program. As an example, if you are loading data into the playground instance, you should define this as:

```vb
Const SERVER_ADDRESS = "https://playground.hydroserver.org/api/sensorthings/v1.1/Observations"
```

The `json_string` is the payload of the POST request. The `http_response` stores the response from the server, and the `post_header` is the constructed header for the POST request sent to the server. You need to construct the `json_string` and `post_header` in the code.

### Constructing the HTTP POST Header

To send a request, you need to construct the POST request header to send to the server. The header needs to contain a valid API-key for the HydroServer workspace into which you are loading data. If you don't have an API-key, you need to set that up first via the Workspace access control window in HydroServer's Data Management App. The Campbell Scientific `HTTPPost()` function automatically prepends `POST /` onto the beginning of the request along with the `Content-Length` parameter. Your construction of the header might look something like the following:

```vb
' Construct the main HTTP POST header string
post_header = "X-API-Key: " & HYDROSERVER_API_KEY & CHR(13) & CHR(10)
post_header &= "Connection: close" & CHR(13) & CHR(10)
post_header &= "accept: application/json" & CHR(13) & CHR(10)
post_header &= "Content-Type: application/json" & CHR(13) & CHR(10)
post_header &= "Cache-Control: no-cache" & CHR(13) & CHR(10)
```

We recommend you declare a constant value `HYDROSERVER_API_KEY` at the beginning of your program that contains the value of your API-Key. In the example above, `CHR(13) & CHR(10)` adds a carriage return and line feed character to the end of each line.

### Constructing the JSON Payload

Observations can be posted to HydroServer via the SensorThings API using two different methods (see the [SensorThings documentation](/user-guides/how-to/loading-data-with-sensorthings.md) for details). This example CR350 program POSTs each individual data value measured one at a time to HydroServer. This uses a straightforward JSON encoding formatted as follows:

```json
{
  "Datastream": {
    "@iot.id": "3fa85f64-5717-4562-b3fc-2c963f66afa6"
  },
  "phenomenonTime": "2023-06-01T10:05:00Z",
  "result": 32.4
}
```

where the `@iot.id` is the UUID of the datastream you are loading data into, the `phenomenonTime` is the timestamp for the data value, and the `result` is the numeric data value that was observed. There is a separate dataArray format you could use for POSTing multiple observation records in a single request (again - see the SensorThings API documentation), but we've kept it simple for this example.

You need to construct this JSON payload from information in your CRBasic program. That means you need to set the values of the UUIDs for each datastream you want to load data into and get the timestamp and data values so you can construct the JSON string. The JSON string construction will look something like the following:

```vb
' Construct the JSON payload to POST to HydroServer for the current data values
' The JSON syntax is minified for compactness
json_string = "{"
json_string &= CHR(34) & "Datastream" & CHR(34) & ":{"
json_string &= CHR(34) & "@iot.id" & CHR(34) & ":"
json_string &= CHR(34) & datastream_uuid & CHR(34) & "},"
json_string &= CHR(34) & "phenomenonTime" & CHR(34) & ":" & time_stamp & ","
json_string &= CHR(34) & "result" & CHR(34) & ":" & data_value & "}"
```

It might be easier to construct this JSON string using the CRBasic `Sprintf()` function, but we've kept it simple here by using simple string concatenation. You need double quotes inside your JSON string, so using `CHR(34)` inserts those directly. In this example, you need to set the following variables:

- `datastream_uuid`: This is the UUID of the datastream you are loading data into.
- `time_stamp`: This is the datetime value associated with the observation string formatted according to the ISO 8601 standard.
- `data_value`: This is the numeric data value you are trying to load.

In the full <a href="/user-guides/how-to/CR350_example.CRB" download>CR350 datalogger example</a>, data for multiple observed variables are loaded into HydroServer. So, the construction of the header and the JSON payload for the `HTTPPost()` request are both contained in a loop within a subroutine we wrote that gets the last record from the program's data table, splits that record into elements, and then loads each data value to HydroServer using a separate `HTTPPost()` function call.

### The Main CRBasic Program

In the CR350 code example, we provide a subroutine that gets the latest row from the program's data table and loads the values from that table into HydroServer. That subroutine should be called on the same frequency at which the data are recorded so that each new data record recorded in the data table also gets sent to HydroServer. Because you may be scanning quickly in your main program and HTTP POST requests can take a little bit of time to send the request and receive the response, we put the code to call the `post_to_hydroserver()` subroutine in a CRBasic `SlowSequence` to enable it to execute independent of the main program scan:

```vb
' Main Program
BeginProg
	Scan (1,Sec,0,0)
	  ' Measurement instructions
		PanelTemp (PTemp,60)
		Battery (Batt_volt)
		' Call Output Tables
		CallTable Output
	NextScan
	SlowSequence
	Scan (1,Min,0,0)
	  ' POST the latest data record from the data table to HydroServer
	  ' Set this Scan rate to match the recording rate for the data table
	  Call post_to_hydroserver()
	NextScan
EndProg
```

The example CR350 program measures the datalogger's panel temperature and battery voltage every 1 second in the main scan interval. In the `SlowSequence` we set a separate scan interval that runs once per minute, which is the same as the data table's recording interval.
