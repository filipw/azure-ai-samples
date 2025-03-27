# Demo

### Prerequisites

 - [Dev Tunnel](https://learn.microsoft.com/en-us/azure/developer/dev-tunnels/get-started) CLI installed
 - [Dotnet SDK](https://dotnet.microsoft.com/download) installed

### Preparation

1. Build the .NET Web API:

```bash
cd webapi
dotnet run
```

This will start a web server on `http://localhost:5270`.

2. Create a dev tunnel in Azure:

```
devtunnel host -p 5270 --allow-anonymous
```

> Important! This sets up an anonymous tunnel. Allowing anonymous access to a dev tunnel means anyone on the internet is able to connect to your local server, if they can guess the dev tunnel ID. Close the tunnel as soon as possible when you are done testing.

This should print the dev tunnel URL:

```
Hosting port: 5270
Connect via browser: https://{TUNNEL ID}.{REGION}.devtunnels.ms
Inspect network activity: https://{TUNNEL URL}.{REGION}.devtunnels.ms

Ready to accept connections for tunnel: {NAME}
```

3. Now set the environment variable `DEV_TUNNEL_URL` to the dev tunnel URL.

### Run the demo

```
python sample.py
```