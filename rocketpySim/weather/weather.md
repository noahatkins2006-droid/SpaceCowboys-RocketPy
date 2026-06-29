This file contains the space cowboys weather tools.
What this means is that we are able to look at weather and use it to simulate the current/future environment
of our launch site.

We use a module that holds a class that we call different functions that we need for our main script.

The reason that we didn't design this within one large script that includes the rocketpy is to keep the code clean and readable. 


-- libraries --

-- spaceweather class: --

    -- class global variables --

    -- hrrr_download function --
        -- compute_fxxx function --

    -- to_env function --




When looking through the file you will first notice the libraries that we use.
Libraries:
_ numpy
_ xarray
_ datetime
_ herbie
_ metpy
_ rocketpy

Numpy is used to manipulate the hrrr data as we need it to work within the rocketpy environment class
Xarray is used to open the hrrr dataset, read it, and filter it for the variables that we are looking for
Datetime is used to return the numerical inputs for date of launch to a string value for the weather system
Herbie is used to pull the hrrr data, it is a library specifically designed for this
Metpy is used to do calculations with weather data
Rocketpy is used to set up the custom envrionment for the rocket to perform in

Needed: 
_ Ability to pull multiple hours of data
_ 