Changelog for EGCG-Core
===========================

0.11.2 (2019-08-07)
-------------------

- AsanaNotification compatibility update for Asana API changes


0.11.1 (2019-07-26)
-------------------

- Updating Jinja2 to 2.10.1
- Updating pyclarity_lims to 0.4.8


0.11 (2019-06-07)
-----------------

 - Make methods to access local NCBI database public
 - Change constant name from gender to sex (breaks backward compatibility)


0.10 (2019-04-04)
-----------------

- Adding LoggingConfiguration.reset
- Removing PBSExecutor
- Removing implicit parameters on cluster jobs, esp. cpu=1 and mem=2
- Allowing Executor to call start() in the same way as other executors
- Process-safe check logging in integration_testing
- Catching all exceptions in Communicator.\_\_del\_\_
- Stricter versions in requirements.txt


0.9.1 (2018-11-22)
------------------

- Adding `-` and `.` to replaceable characters in `clarity.sanitise_user_id`
- Making Session objects unique to child processes in `rest_communication` 


0.9 (2018-09-14)
----------------

- Breaking change: removed `clarity.get_expected_yield_for_sample`
- Catching notification failures
- Added retries and multiprocessing lock to `rest_communication`
- Added log warnings to `util.find_file`
- Added `integration_testing` library and runner


0.8.2 (2018-05-28)
------------------

- New constant to record number of Phix reads 


0.8.1 (2018-02-09)
------------------

- New constants capturing the Interop metrics
- New function for querying dict with dot notation


0.8 (2017-11-29)
----------------

- New EmailSender class that take most of the feature of EmailNotification 


0.7.5 (2017-11-23)
------------------

- update constants: Remove expected yield and add more explicit required yield/yieldQ30/coverage
- code refactor 


0.7.4 (2017-10-31)
------------------

- Bugfix in archive management.
- Add Picard and mapping stats constants


0.7.3 (2017-09-01)
------------------

- Fixed RecursionError when calling `get_documents` on large collections with `all_pages=True`
- Add new option to rest_communication.post_entry to submit payload without json


0.7.2 (2017-08-03)
------------------

- Allow Lims cached connection to be overridden


0.7.1 (2017-06-08)
------------------

- Fix data release workflow name


0.7 (2017-06-08)
----------------

- Add ability to upload files through `rest_communication`
- New functions for finding and routing to clarity steps
- Notifications (email, asana and log) can now accept attachments
- Added a retry in archive_management.register_for_archiving


0.6.12 (2017-05-16)
-------------------

- add new constants to store trimming/filtering of run elements 


0.6.11 (2017-05-04)
-------------------

- get_genome_version can check the config file for the default version if species is provided


0.6.10 (2017-04-26)
-------------------

- Simplify Configuration classes to have only one that support all use-cases 
- New send_mail function for sending one email

0.6.9 (2017-03-24)
------------------

- Enforced the usage of `log_cfg.set_log_level()` rather than modifying `log_cfg.log_level`
- More error reporting in archive_management
- Removed unused Executor file path validation
- Added 204 to Communicator.successful_statuses
- Fixed a bug where `If-Match` was not passed to Communicator._req when using token auth
- Updated `asana` to 0.6.2

0.6.8 (2017-03-15)
------------------
- Added `DATASET_RESUME` to constants

0.6.7 (2017-02-23)
------------------
 - First version to support release on Pypi
 - Add support for dealing with lfs hsm_x command to manage the archive.
 - Add get_genome_version in clarity functions

0.6.5
-----
 - Fix `get_project`

0.6.4
-----
- executors now retry their job submissions upon failure, up to three times
- some log messages from notifications have been reduced to debug
- `clarity.get_sample_gender` now checks for a 'Sex' UDF before checking 'Gender'
- in `rest_communication`, the building of requests has been fixed, as below:

In Communicator.get_content, we used to build a url manually via `api_url` and pass it to `_req`. This was because we had to cast dicts to strings manually:

```python
where = {'this': 'that', 'other': None}
cast_where = '{"this":"that","other":null}'
```

However, the removal of spaces that this involved meant that any query for a field containing a space resulted in a bad query:

```python
where = {'field_name': 'with spaces'}
cast_where = '{"field_name":"withspaces"}'
```

To fix this, we now pass the query string through [params](http://docs.python-requests.org/en/master/user/quickstart/#passing-parameters-in-urls), and do Json serialisation on any dict params:

```python
params = {'page': 1, 'where': {'this': 'that', 'other': None}}
query_string = '?page=1&where={"this": "that", "other": null}'
```

0.6.3  
-----

0.6.2
-----
Emergency fix in move_dir where the destination file was named after the linked file instead of the link name
Downloads


0.6.1
-----
Improve util and error handling
Add function to retrieve project from LIMS API

0.6
---
 
This version adds the ability to cancel currently running cluster jobs in executor. Also fixes a bug in util.move_dir.

0.5.1
-----

Minor version adding evenness

0.5
---

Executors have been fixed to process the output of sacct properly. Script writers have also been refactored/simplified.
Downloads

0.4.4
-----
 
0.4.3
-----

This version add the ability to Notify a log file, through email or over Asana tasks.
It also adds new constant and allow the Configuration object to still work even when no config file is passed

0.4.2  
-----

0.4.1
-----

This version fixes a bug in `EnvConfiguration`, where it wasn't selecting a new environment properly. Two fields have also been added to `constants` for upcoming versions of Analysis-Driver and Reporting-App.

0.4
---
Bugs have been fixed in `clarity`, `ncbi` and `rest_communication`. There is also now a more flexible, object oriented `rest_communication`, where a `Communicator` object can be created with a base url and username-password or token authentication.


0.3.1
-----
This adds a new field for Y-chromosome coverage to `constants`

0.3
---
This version is able to send authentication headers in `rest_communication` transactions. It now implements lazy loading of database connections and configs, so it is possible to, e.g, import rest_communication without importing ncbi, which requires sqlite3. It also allows egcg_core.config to switch its config file, allowing client apps to do, in `__init__.py`:

``` python
import egcg_core.config
egcg_core.config.cfg.load_config_file('/path/to/a_config.yaml')
# executors, ncbi, etc, can now use the same config file as the client app
```


0.2.4
-----
Since 0.2.1, this project now stores version information in __init__.__version__. A field for EdinburghGenomics/EGCG-Project-Management has also been added to constants, and an executor bug has been fixed.

0.2.3
-----

0.2.2
-----

0.2.1
-----
This version moves the deployment from distutils to setuptools, allowing automatic installation of subdependencies when EGCG-Core is installed as a requirement from another project.

0.2
---
This version adds functions to `util` specific to finding Fastqs, that previously lived in EdinburghGenomics/Analysis-Driver.

0.1 
---
First version of the EGCG-Core package
