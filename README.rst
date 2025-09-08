Odoo Development Tutorial
==========================

This repository contains the developed application covered in `Server Framework 101 <https://www.odoo.com/documentation/18.0/developer/tutorials/server_framework_101.html>`__ Odoo Developer tutorial.
Please follow `Setup Guide <https://www.odoo.com/documentation/18.0/developer/tutorials/setup_guide.html>`__ and `Source Installation <https://www.odoo.com/documentation/18.0/administration/on_premise/source.html>`__ to checkout and setup Odoo locally.
Once Odoo is cloned, clone this repository as a sibling of odoo directory. Make sure Postgresql is running and you have created a new database for this tutorial. For this repository, `odoo_18_community` named database is used.

* Open the terminal and cd into odoo directory (whether community or enterprise)
* Run the command ``python odoo-bin --addons-path=addons,../ -d odoo_18_community -u estate --dev xml``

  * This command includes the default Odoo addons and any apps in a directory one level up. If you have cloned this repository in a different directory, please add that path in addons-path and remove **../**
  * -d odoo_18_community is the database name. Change the name if you plan to use a different database name.
  * -u estate means the estate app added by this repository should be updated when the server is run.
  * --dev xml allows refreshing of XML views without having to restart the server

* Once the command completes, access the server on http://localhost:8069/.
* Enable estate app from Apps section. Once re-loaded, you should be able to interact with estate apps
