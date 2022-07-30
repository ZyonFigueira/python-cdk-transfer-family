#!/usr/bin/env python3
import os

import aws_cdk as cdk

from transfer_family.transfer_family_stack import TransferFamilyStack


app = cdk.App()
TransferFamilyStack (app, "transfer-family")

app.synth()
