# Security, Privacy & Explainability in ML (SPEML SS2025)
## Exercise: Attacking Data Fingerprints
[Data fingerprints](fingerprinting.md) are used as a method for tracing unauthorised redistribution of the data and ownership protection.
The fingerprint (sometimes also called a personalised watermark) is a bit-string that carries information about the legitimate owner of the data and the recipient of the specific copy and gets embedded into the content (data) via a secure pattern.
Fingerprints can be reliable tools for asserting ownership and tracing data leakage, however their effectiveness can be broken by different data manipulation techniques. 

>**Your task in this exercise is to hack the fingerprint :)**

### Exercise description
This exercise is organised into two phases:
1. **Phase 1: Break the fingerprint!** -- In this phase you will get one fingerprinted dataset copy and act maliciously in the attempt to remove the fingerprint. See the details [here](phase1.md).
2. **Phase 2: Collusion attack** -- In this phase you will have access to multiple fingerprinted copies to achieve the same malicious goal. See the details [here](phase2.md).

### Submission guidelines
The exercise is evaluated based on the detail and the reproducibility of the report. 
You are expected to describe your attempts (successful and failed), your thought process and reasoning and answer in detailed the questions associated to each phase.
Attack success is an important factor, but will not be the deciding one when it comes to grading. 

The submission guidelines and deadlines are available [here](submission.md).

### Datasets, methods and support
For each phase, you will obtain the datasets to work with. You can access the data [here](datasets.md).

If you are interested to explore fingerprinting in more detail, you can read the [documentation](fingerprinting.md) and access the code. 
If you have any questions, you can always write in TUWEL or send us an email.

>Happy hacking! :computer:
