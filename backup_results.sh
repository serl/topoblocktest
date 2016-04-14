#!/bin/bash

RESULTS_DIR=results/

tar -cjf backup/results_`date +"%Y%m%d-%H%M%S"`.tar.gz "$RESULTS_DIR"
