librarian::shelf(tidyverse, jsonlite, stringr, janitor, tools, fs, here, usethis)

csv_files <- Sys.glob(file.path("./wait_times", "*.csv"))

configs = NULL
sequences = NULL
for(csv_file in csv_files){
  file_path_sans_ext <- tools::file_path_sans_ext(csv_file)
  sequence_id <- path_file(file_path_sans_ext)
  json_file <- sprintf("%s.jsonl", file_path_sans_ext)
  lines <- readLines(jsonl_file)
  
  # assemble the config elements into a tibble
  if(is.null(configs)){
    configs <- lapply(lines[1], fromJSON)  %>% 
      #  # flatten the items
      lapply(unlist) %>% 
      bind_rows() %>%
      clean_names() %>%
      as_tibble() %>%
      mutate(sequence_id=sequence_id) 
    
    sequences <- read_csv(file=csv_file) %>%
      select(-last_col()) %>%
      clean_names() %>%
      as_tibble() %>%
      mutate(sequence_id=sequence_id) %>%
      tibble::rowid_to_column("index") %>%
      select(c(sequence_id,
               index, 
               mean_vehicle_count, 
               vehicle_fraction_idle,
               vehicle_fraction_picking_up, 
               vehicle_fraction_with_rider,
               mean_trip_wait_fraction,
               mean_trip_wait_time)) %>%
      pivot_longer(cols = c("vehicle_fraction_idle", 
                          "vehicle_fraction_picking_up", 
                          "vehicle_fraction_with_rider", 
                          "mean_trip_wait_fraction",
                          "mean_trip_wait_time"),
                       names_to="measure",
                       values_to="value")
  } else {
    this_config <- lapply(lines[1], fromJSON)  %>% 
      #  # flatten the items
      lapply(unlist) %>% 
      bind_rows() %>%
      clean_names() %>%
      mutate(sequence_id=sequence_id) 
    configs <- union(configs, this_config)
    
    this_sequence <- read_csv(file=csv_file) %>%
      select(-last_col()) %>%
      clean_names() %>%
      as_tibble() %>%
      mutate(sequence_id=sequence_id) %>%
      tibble::rowid_to_column("index") %>%
      select(c(sequence_id,
               index, 
               mean_vehicle_count, 
               vehicle_fraction_idle,
               vehicle_fraction_picking_up, 
               vehicle_fraction_with_rider,
               mean_trip_wait_fraction,
               mean_trip_wait_time)) %>%
      pivot_longer(cols = c("vehicle_fraction_idle", 
                            "vehicle_fraction_picking_up", 
                            "vehicle_fraction_with_rider", 
                            "mean_trip_wait_fraction",
                            "mean_trip_wait_time"),
                   names_to="measure",
                   values_to="value")
    sequences <- union(sequences, this_sequence)
  }
}
usethis::use_data(configs)
usethis::use_data(sequences)
