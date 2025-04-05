# AWS S3 Bucket Misconfiguration Scanner

A Python tool to scan AWS S3 buckets for permission misconfigurations and security vulnerabilities.

## Overview

This tool helps security professionals and AWS administrators identify potentially dangerous permission settings in S3 buckets. It checks multiple permission types on each bucket and prefix, highlighting those that might represent security risks.

## Features

- Scan individual buckets or multiple buckets from a list
- Auto-detection of regions from bucket URLs
- Support for various bucket name formats
- Detailed permission testing:
  - List objects (`ls`)
  - Upload files (`cp`)
  - Move files (`mv`)
  - Delete files (`rm`)
  - Download files (`cp from`)
- Color-coded output highlighting potential security issues
- Comprehensive summary report

## Requirements

- Python 3.6+
- AWS CLI installed and configured
- Valid AWS credentials with permissions to test S3 operations
## Installing and Configuring AWS CLI

Before using the S3 Bucket Misconfiguration Scanner, you need to install and configure the AWS Command Line Interface (CLI).

### Installing AWS CLI

#### On Windows:
1. Download the AWS CLI MSI installer from the [AWS CLI website](https://aws.amazon.com/cli/)
2. Run the downloaded MSI installer and follow the instructions
3. Verify installation by opening Command Prompt and typing:
   ```
   aws --version
   ```

#### On macOS:
Using Homebrew:
```bash
brew install awscli
```
Or with pip:
```bash
pip install awscli
```

#### On Linux:
Using pip:
```bash
pip install awscli
```
Or on Debian/Ubuntu:
```bash
sudo apt-get update
sudo apt-get install awscli
```

### Configuring AWS CLI

1. Get your AWS access key ID and secret access key from the AWS Management Console
   - Log in to the AWS Management Console
   - Click on your username at the top right and select "Security credentials"
   - Under "Access keys", create a new access key

2. Configure AWS CLI using your credentials:
   ```bash
   aws configure --profile PROFILE_NAME
   ```

3. Enter the requested information:
   ```
   AWS Access Key ID: YOUR_ACCESS_KEY
   AWS Secret Access Key: YOUR_SECRET_KEY
   Default region name: YOUR_PREFERRED_REGION (e.g., us-east-1)
   Default output format: json
   ```

## Installation

1. Clone this repository:
   ```bash
   git clone https://github.com/yourusername/s3-bucket-scanner.git
   cd s3-bucket-scanner
   ```
2. Install dependencies:
   ```bash
   pip3 install -r requirements.txt
   ```
3. Make the script executable:
   ```bash
   chmod +x s3-bucket-scanner.py
   ```

## Usage

### Scanning a Single Bucket

```bash
./s3-bucket-scanner.py -b BUCKET_NAME -p AWS_PROFILE [-r REGION]
```

### Scanning Multiple Buckets

```bash
./s3-bucket-scanner.py -l BUCKET_LIST_FILE -p AWS_PROFILE [-r REGION]
```

### Bucket Name Formats

When providing bucket names (either with `-b` or in a bucket list file), you can use:

1. Full S3 URL with region: `mybucket.s3-us-west-1.amazonaws.com`
   (Region will be automatically extracted and used)

2. Full S3 URL without region: `mybucket.s3.amazonaws.com`
   (Only bucket name "mybucket" will be extracted)

3. Simple bucket name: `mybucket`
   (Will use default region or specified region via `-r` option)

### Command Line Options

```
  -b, --bucket BUCKET_NAME    Scan a single S3 bucket
  -l, --list FILE_PATH        Path to a file containing bucket names (one per line)
  -p, --profile PROFILE_NAME  AWS CLI profile to use for authentication
  -r, --region REGION_NAME    AWS region to use (e.g., us-east-1, eu-west-1)
  -h, --help                  Display this help message
```

## Examples

### Scan a single bucket

```bash
./s3-bucket-scanner.py -b my-bucket -p default
```

### Scan a single bucket with a full URL

```bash
./s3-bucket-scanner.py -b my-bucket.s3-eu-west-1.amazonaws.com -p default
```

### Scan a single bucket in a specific region

```bash
./s3-bucket-scanner.py -b my-bucket -p default -r eu-west-1
```

### Scan multiple buckets listed in a file

```bash
./s3-bucket-scanner.py -l my_buckets.txt -p prod-account -r us-west-2
```

## Output

### Scanning Multiple Buckets
![usage-output](https://github.com/user-attachments/assets/3404f5c9-3c53-4c7b-8a86-7a1c6b45bd43)

### Scanning Single Bucket
![image](https://github.com/user-attachments/assets/3e65d6e2-b2ae-4542-84f3-c2dab369c991)

## Security Notes

- This tool performs actual operations on S3 buckets to test permissions
- Test files are created and deleted during the scanning process
- Use with caution on production environments
- Ensure you have appropriate permissions before scanning buckets

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.
