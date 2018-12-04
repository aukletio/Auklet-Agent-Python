<p align="center"><a href="https://auklet.io"><img src="https://s3.amazonaws.com/auklet/static/auklet_python.png" alt="Auklet - Problem Solving Software for Python"></a></p>

# Auklet for Python
<a href="https://pypi.python.org/pypi/auklet" alt="PyPi page link -- version"><img src="https://img.shields.io/pypi/v/auklet.svg" /></a>
<a href="https://pypi.python.org/pypi/auklet" alt="PyPi page link -- Apache 2.0 License"><img src="https://img.shields.io/pypi/l/auklet.svg" /></a>
<a href="https://pypi.python.org/pypi/auklet" alt="Python Versions"><img src="https://img.shields.io/pypi/pyversions/auklet.svg" /></a>
[![Maintainability](https://api.codeclimate.com/v1/badges/4217e03b794e778bd0d0/maintainability)](https://codeclimate.com/github/aukletio/Auklet-Agent-Python/maintainability)
[![Test Coverage](https://api.codeclimate.com/v1/badges/4217e03b794e778bd0d0/test_coverage)](https://codeclimate.com/github/aukletio/Auklet-Agent-Python/test_coverage)

This is the official Python agent for [Auklet][brochure_site]. It officially supports Python 2.7.9+ and 3.4-3.7, and runs on most POSIX-based operating systems (Debian, Ubuntu Core, Raspbian, QNX, etc).

## Features
- Automatic report of unhandled exceptions
- Automatic Function performance issue reporting
- Location, system architecture, and system metrics identification for all issues
- Ability to define data usage restriction


## Compliance
Auklet is an edge first application performance monitor; therefore, starting with version 1.0.0 we maintain the following compliance levels:

- Automotive Safety Integrity Level B (ASIL B)

If there are additional compliances that your industry requires please contact the team at <hello@auklet.io>.

## Quickstart
To install the agent with _pip_:

```bash
pip install auklet
```

To setup Auklet monitoring in your application:

```python
from auklet.monitoring import Monitoring
auklet_monitoring = Monitoring(
    api_key="<API_KEY>",
    app_id="<APP_ID>",
    release="<CURRENT_COMMIT_HASH>"
)
auklet_monitoring.start()
# Call your main function
main()
auklet_monitoring.stop()
```

### Authorization
To authorize your application you need to provide both an API key and app ID. These values are available in the connection settings of your application as well as during initial setup.

### Optional: Release Tracking
You can track releases and identify which devices are running what variant of code. To do this, you may provide the git commit hash of your deployed code and a version string you can modify. This release value should be passed into the constructor through the release argument, and your custom version should be passed via the version argument. The release value must be the git commit hash that represents the deployed version of your application. The version value is a string that you may set to whatever value you wish to define your versions. Please note that you can provide either a release value, version value, or both.
* Providing <strong>release</strong> enables code snippets to be shown for identified errors if you’ve linked your GitHub.
* Including <strong>version</strong> allows you to track what version of code had the issue.

```bash
curl -X POST https://api.auklet.io/v1/releases/ \
            -H "Content-Type: application/json" \
            -H "Authorization: JWT <API_KEY>" \
            -d '{"application": "<APP_ID>", "release": "'$(git rev-parse HEAD)'", "version": "<YOUR_DEFINED_VERSION>"}'
```

#### Get Release via Subprocess
If you package and deploy your entire Git repository (including the `.git` directory), and if you have `git` installed on your devices, you can get the commit hash via a subprocess:

```python
git_commit_hash = subprocess.check_output(['git', 'rev-parse', 'HEAD'])
                  .decode('utf8').strip('\n')
```

#### Get Release via Environment Variable
If you package your app and deploy it without access to `git`, you can pass the commit hash to your app using the environment variable `APPLICATION_GIT_COMMIT_HASH`:

```python
git_commit_hash = os.environ.get("APPLICATION_GIT_COMMIT_HASH")
```

#### Get Release via File
Lastly, if it is difficult or impossible to set an environment variable via your deployment platform, you can include a new file in your packaged deployment which contains the commit hash. You can read from this file and supply the value to the constructor.

At packaging time, write the commit hash to a file and then include it in your package:

```bash
git rev-parse HEAD > path/to/git_commit_hash.txt
```

At runtime, read the included file as follows:

```python
release_file = open("git_commit_hash.txt", "r")
git_commit_hash = release_file.read().decode('utf8').strip('\n')
```

#### Define Your Own Version
You can also provide your own version string in the constructor:

```python
from auklet.monitoring import Monitoring
auklet_monitoring = Monitoring(
    api_key="<API_KEY>",
    app_id="<APP_ID>",
    release="<CURRENT_COMMIT_HASH>",
    version="<DEFINED_VERSION>"
)
```

## Questions? Problems? Ideas?

To get support, report a bug or suggest future ideas for Auklet, go to https://help.auklet.io and click the blue button in the lower-right corner to send a message to our support team.

## Resources
- [Auklet][brochure_site]
- [Python Documentation](https://docs.auklet.io/docs/python-integration)

[brochure_site]: https://auklet.io
