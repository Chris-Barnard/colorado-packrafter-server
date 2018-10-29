#!/bin/bash
echo "hello, $USER"
echo "starting flowbot tasks"
PYTHONPATH="/home/ec2-user/luigi/flowbot/" /usr/local/bin/luigi --module tasks Flowbot
