
# coding: utf-8

# In[124]:


import pandas as pd
from sqlalchemy import create_engine
import requests

from sqlalchemy.types import NVARCHAR, INT, DECIMAL, DATETIME
import credentials

# # Define functions that drive program flow

# ### Define Function to scrape AWW

# In[178]:


def grab_flow(url):
    print('Querying American White Water : ',url)
    header = {
      "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/50.0.2661.75 Safari/537.36",
      "X-Requested-With": "XMLHttpRequest"
    }

    try:
        r = requests.get(url, headers=header, timeout=13.05)
        dfs = pd.read_html(r.text.encode('utf-8'))

        flowchart = dfs[0]

        # grab relevant information out of the results table 
        flow_string = flowchart.iloc[4,1].split(' ')[0]
        guage_name = flowchart.iloc[2,1]
        flow_last_updated = flowchart.iloc[4,0].split(': ')[1]

        if(flow_string.isnumeric() == False):
            if('.' in flow_string):
                flow = float(flow_string)
            else:
                raise Exception('Error processing flowchart - returned non numeric flow')
        else:
            flow = int(flow_string)

    except Exception as e:
        #raise e
        print('Error reading data from {}'.format(url))
        return dict(flow=0, guage='none', flow_last_updated='n/a')

    return dict(flow=flow, guage=guage_name, flow_last_updated=flow_last_updated)



# ### Load in the targets file

# In[53]:


def load_flow_targets():
    conn_string = credentials.database['conn_string']

    print(conn_string)
    print('creating engine: ')
    engine = create_engine(conn_string)

    print('running sql')

    df2 = pd.read_sql('SELECT * FROM coloradopackrafter.flowbot_requests;', engine)
    print(df2)

    return df2


# ### Perform the AWW url scrape for each unique url in our list of targets

# In[179]:


def lookup_current_values(targets):
    urls_to_lookup = targets.url.drop_duplicates().tolist()

    results = dict()
    for url in urls_to_lookup:
        results[url] = grab_flow(url)

    return results


# ### Create function to evaluate conditions to keep checking or send email

# In[121]:


def evaluate(target):
    print(target)
    target.loc[(target.type == 'OVER') & (target.cur_flow >= target.target), 'evaluation'] = True
    target.loc[(target.type == 'UNDER') & (target.cur_flow <= target.target), 'evaluation'] = True
    
    return target.evaluation.fillna(False)


# # Function to lookup targets and decide who gets an email
# ### This is simple now that everything has been defined
#  - load in targets and urls
#  - lookup current values for each url
#  - Now we map our current values to our targets table by url
#  - And then evaluate whether our trigger has hit or not
#  - generate list to email and new target list

# In[185]:


def process_targets():
    targets = load_flow_targets()
    cur_values = lookup_current_values(targets)

    results = (
        targets
        .assign(cur_flow=lambda x: x.url.map(cur_values).apply(lambda x: x['flow']))
        .assign(guage_name=lambda x: x.url.map(cur_values).apply(lambda x: x['guage']))
        .assign(flow_last_updated=lambda x: x.url.map(cur_values).apply(lambda x: x['flow_last_updated']))
        .assign(evaluation=evaluate)
    )

    email_list = (
        results
        .query('evaluation == True')
    )

    email_list.to_pickle('/home/ec2-user/luigi/flowbot/runtime-data/email_list.pkl')

    new_target_list = (
        results
        .query('evaluation == False')
        #.loc[:, ['email','url','type','value']]
    )

    new_target_list.to_pickle('/home/ec2-user/luigi/flowbot/runtime-data/targets.pkl')
    
    return email_list, new_target_list


# In[192]:

def remove_target(id):
    
    conn_string = credentials.database['conn_string']

    print(conn_string)
    print('creating engine: ')
    engine = create_engine(conn_string)

    print('removing item')
    engine.execute('delete from coloradopackrafter.flowbot_requests where id={}'.format(id))
    
    return None

def add_target(data):

    conn_string = credentials.database['conn_string']

    engine = create_engine(conn_string)

    sql = """
    insert into `coloradopackrafter`.`flowbot_requests` (`url`,`type`,`target`,`email`,`date_added`) values ('{}', '{}', '{}', '{}','{}')
    """.format(data['url'], data['type'].upper(), data['target'], data['email'], pd.Timestamp('now', tz='utc'))

    engine.execute(sql)

    return True

def log_email_sent(item):
    conn_string = credentials.database['conn_string']
    engine = create_engine(conn_string)

    print('Logging sent email')
    print(item)

    sql = """
    insert into `coloradopackrafter`.`flowbot_emails_sent` (`url`,`type`,`target`,`email`,`cur_flow`,`guage_name`,`request_id`,`date_sent`) values ('{}','{}','{}','{}','{}','{}','{}','{}')
    """.format(item.url, item.type.upper(), item.target, item.email, item.cur_flow, item.guage_name, item.id, pd.Timestamp('now', tz='utc'))

    engine.execute(sql)

    return True


# # Craft an email message

# In[211]:


import sys
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def make_email(item):
    outer = MIMEMultipart()
    outer['Subject'] = 'FLOWBOT Automated Email: {0} guage has achieved a flow of {1}'.format(item.guage_name, item.cur_flow)
    outer['To'] = item.email
    outer['From'] = 'flowbot@coloradopackrafter.com'
    htmlText = """
    <html>
        <body>
            <h1>Flowbot @ ColoradoPackrafter</h1>
            <h3>
                Dear Packrafter,
            </h3>
            <p>
                You previously set an alert {4} days ago for the guage: {0} {1} {2}
                <br />
                Well, the current flow has reached {3}, so now you are getting this message.  So get out there and be safe!
            </p>
            <p>
            </p>
        </body>
    </html>
    """.format(item.guage_name, item.type.lower(), item.target, item.cur_flow, (pd.Timestamp('now') - pd.Timestamp(item.date_added)).days)
    
    outer.attach(MIMEText(htmlText, 'html'))
    
    return outer.as_string()

def save_results():
    conn_string = credentials.database['conn_string']
    engine = create_engine(conn_string)
    engine.execute('drop table `coloradopackrafter`.`flowbot_latest_results`')
    data = pd.read_pickle('/home/ec2-user/luigi/flowbot/runtime-data/targets.pkl')
    types = {
        'url' : NVARCHAR(length=255),
        'type' : NVARCHAR(length=255),
        'email' : NVARCHAR(length=255),
        'target' : DECIMAL(10,5),
        'cur_flow' : DECIMAL(10,5),
        'guage_name' : NVARCHAR(length=255),
        'flow_last_updated' : NVARCHAR(length=255),
        'id' : INT(),
        'evaluation' : INT(),
    }
    print(data.head(25))
    data.to_sql('flowbot_latest_results', engine, if_exists='replace', dtype=types, index=False)

    print('Results saved to DB\n\n')
    return True

def send_email(item):
    username = credentials.email['username']
    password = credentials.email['password']
    s = smtplib.SMTP(credentials.email['server'], 587)
    s.ehlo()
    s.starttls()
    s.login(username, password)
    s.sendmail('flowbot@coloradopackrafter.com', item.email, make_email(item))
    s.quit()
    print('Email Sent!')

def run_flowbot():

    print('Entering Main Function ---------------------------------')
    email_list, targets = process_targets()
    print('Emails to send: ', len(email_list))
    print('Targets Remaining: ', len(targets))


    for item in email_list.itertuples():
        try: 
            log_email_sent(item)
            send_email(item)
            remove_target(item.id)
        except:
            print('Unable to send', sys.exc_info()[0])
            raise

if __name__ == '__main__':
    grab_flow('https://www.americanwhitewater.org/content/River/detail/id/402')
