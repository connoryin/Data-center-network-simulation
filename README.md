# Project
This repo contains sample JSON files for this project. sfc_\<num\>.json shows JSON samples used to register a chain. launch_sfc_\<num\>.json shows JSON samples used to launch NF instances for a chain, and scale_sfc_\<num\>.json shows JSON samples used to scale and add additional NF instances for a chain.
  
You can use the following workflow to test your implementation:

1. `./step0_initialize_infra.sh`
2. `./step1_register.sh`
3. `./step2_launch.sh`
4. `./step3_scaleup.sh`

Finally you need to build a traffic generator that generates traffic between Docker containers based on the a profile of the format present in `traffic_profile.json`.
