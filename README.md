# LinkedIn Job Scraper

This is a job scraper that scrapes LinkedIn job postings using Selenium. It was created to help aid my internship hunt because nobody has time to sift through hundreds of job postings to find the ones that are relevant to them. 

This is heavily based on [LinkedIn-Easy-Apply-Bot](https://github.com/nicolomantini/LinkedIn-Easy-Apply-Bot) by nicolomantini. Most of the webscraping code is from that repository, with my modifications of parsing job descriptions, filtering out irrelevant job postings, and sending notifications to Discord.

## Installation

Forewarning: This is a very rough implementation and was not necessarily designed with the idea of being used by others. It may take some manual work to get it up and running and sufficient for your use case.

Tested on macOS, Python 3.12

1. Clone the repository using `git clone`
2. Create a virtual environment using `python3 -m venv venv`
3. Install the requirements using `pip install -r requirements.txt`
4. Configure the `config.yaml` file (refer to `config.yaml.example` for an example)
5. For first time use, set the `retrieveCookies = False` in `main.py` to `True` to log in to LinkedIn and save the cookies
6. Run the script using `python3 main.py`

## Usage

This script will iterate through different job title queries and scrape the job postings for each query. It will then scan the description for specific keywords. Postings with 3+ keywords will be sent to you via a Discord webhook for ease-of-notification (you can just run this script in the background and wait for the notifications!!!). 

## Configuration

```yaml
username: email@email.com
password: password
webhook: https://discord.com/api/webhooks/1234567890/abcdefghijklmnopqrstuvwxyz

# Position queries to search for
positions:
- Finance Intern
- Investment Banking Intern
- Investment Banking Summer Analyst
- Financial Advisory Intern
- Financial Analyst Intern
- Marketing Intern
- Business Development Intern
- Accounting Intern

# Locations to search for
# You can use 'Remote' to search for remote positions
# Any other location will just be ignored as-is, but you can fix the code (it's just a commented out line)
locations:
- USA

blacklistCompanies:
- WayUp

blackListTitles:
- SkillBridge
- Skill Bridge

keywords:
- excel
- invest
- sales
- budget
- analysis
- analytical
- stock
- asset management
- risk management
- portfolio
- equity
- regulations
- equity
- capital
```

## Contributing

Not accepting contributions at this time. Feel free to fork the repository and make your own changes.

## License
