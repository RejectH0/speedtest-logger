#!/bin/bash
crontab -l | cat - crontab.txt | crontab -
