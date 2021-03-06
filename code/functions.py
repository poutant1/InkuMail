import os
import shutil
import re
import codecs
import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.header import Header
from tempfile import mkstemp
from shutil import move
from code.bs4 import BeautifulSoup, Comment
    
'''
compile_newsletter()
This is the mother function, which constructs all the differents versions of the
newsletter (MIME, plain text, web) from the articles, and saves them in the 
'active' folder of the appropriate newsletter type.
    PARAMETERS:
        - the Newsletter object, which will be used to hold all the articles 
          during construction
        - a tk.Progressbar object, which will be progressed and updated
          along the way
    RETURNS:
        - a boolean value. This is True if there were no errors during 
          execution, False otherwise
        - the same Newsletter object that was received, without any of the articles.
'''
def compile_newsletter(newsletter, progressbar, bolding):
    
    #Remove the articles from the newsletter, so they won't be duplicated if 
    #the function is run a second time
    if not bolding:
        newsletter.clear_articles()

    #Store the address of the parent folder for later recall
    parent_folderpath = os.getcwd()
   
    newsletter_type = newsletter.get_newsletter_type()
    progressbar.step(10.0)
    progressbar.update()
    
    #read in the templates
    #html_template_filename = "templates/email_html_template.html"
    #web_template_filename = "templates/web_template.html"
    
    #with open(web_template_filename, "r") as web_template_file:
    #    web_template = web_template_file.readlines()
        
        
    progressbar.step(10.0)
    progressbar.update()    
        
    html_template = generate_soup(newsletter, "MAIL").split("\n")
    web_template = generate_soup(newsletter, "WEB").split("\n")
    
    progressbar.step(10.0)
    progressbar.update()
        
    #extract the articles from their files
    articles_folderpath = get_article_folderpath(newsletter_type)
    if not bolding:
        try:
            os.chdir(parent_folderpath + articles_folderpath)
        except OSError as e:
            return False, e
        
        for filename in sorted(os.listdir(os.getcwd())):
            if filename.endswith(".txt"):
                add_article(newsletter, filename)
    
    progressbar.step(10.0)
    progressbar.update()
    
    #Format html links separately
    if not bolding:
        format_links_to_html(newsletter)
    
    progressbar.step(10.0)
    progressbar.update()
    
    #Generate the different html-documents
    html_version = generate_html_version(html_template, newsletter, "MAIL")
    web_version = generate_html_version(web_template, newsletter, "WEB")
    
    progressbar.step(10)
    progressbar.update()

    #Generate plain text version
    plain_text_version = generate_plain_text_version(newsletter)
    
    progressbar.step(10.0)
    progressbar.update()
    
    #Combine the html and plain text version into the MIME-verrsion
    MIME_version = generate_MIME_version(newsletter, html_version, plain_text_version)
        
    progressbar.step(10.0)    
    progressbar.update()
        
    #Change writing directory to the appropriate folder
    os.chdir(parent_folderpath)
    
    #Prepare the filenames where the text will be written
    html_filename = "email_html_version.html"
    plain_filename = "plain_text_version.txt"
    MIME_filename = "MIME_version.eml"
    web_filename = "web_version.html"
    
    #Write the generated text into files
    active_folderpath = parent_folderpath + get_active_folderpath(newsletter_type)
    try:
        os.chdir(active_folderpath)
    except OSError as e:
        return False, e
    
    with open(html_filename, "w", encoding = "utf-8") as html_file:
        html_file.write(html_version)
    with open(plain_filename, "w", encoding = "utf-8", newline = "\n") as plain_text_file:
        plain_text_file.write(plain_text_version)
    with open(MIME_filename, "w", encoding = "utf-8") as MIME_file:
        MIME_file.write(MIME_version.as_string())
    with open(web_filename, "w", encoding = "utf-8") as web_file:
        web_file.write(web_version)
        
    progressbar.step(10.0)    
    progressbar.update()
    
    #Return to the parent folder
    os.chdir(parent_folderpath)

    
    return True, newsletter

'''
archive_files()
This function is called once the newsletter has been sent. It copies all the
files in the 'active' folder into an archive folder of the appropriate 
newsletter type.
    PARAMETERS:
        - The Newsletter object to be saved
        - the folderpath to the 'active' folder, containing the different versions
          of the sent mail. Represented as a string.
    RETURNS:
        - nothing
'''
def archive_files(newsletter, active_folderpath):
    
    #Get the proper folder. If one doesn't exist, create it.
    parent_folderpath = os.getcwd()
    archive_folderpath = parent_folderpath + get_archive_folderpath(newsletter)
    if not os.path.isdir(archive_folderpath):
        os.makedirs(archive_folderpath)
    
    for filename in os.listdir(active_folderpath):
        shutil.copyfile(active_folderpath + filename, \
                        archive_folderpath + "/" + filename)


'''
convert_to_UTF8()
converts a given text file into UTF-8 format
    PARAMETERS: 
        - the name of the file to be converted. The file must be in the folder
          where this code will be executed
    RETURNS:
        - nothing
'''
def convert_to_UTF8(fileName):
    
    #Try to guess the format of the file
    sourceFormats = ['us-ascii',  'windows-1252', 'iso-8859-1', 'utf-8-sig']
    
    #Prepare a temporary location for the conversion file
    fh, abs_path = mkstemp()
    
    #For each guess, try to convert it to UTF-8 
    for current_format in sourceFormats:
        try:
            #Open the given file with the guessed format
            sourceFile = codecs.open(fileName, 'rU', current_format) 
            
            #Open the temporary conversion file in UTF-8 format
            temp = open(abs_path, "w", encoding = "utf-8", newline = "\n")
            
            #Try to write the text from the source file to the temporary file
            text = sourceFile.read()
            temp.write(text)
            
            #close stream channels
            os.close(fh)
            sourceFile.close()
            temp.close()
            
            #Remove the original file
            os.remove(fileName)
            
            #write the temporary file into the location of the original file
            move(abs_path, fileName)
            return
        except UnicodeDecodeError:
            pass
    #If none of the guesses turned out to be right, signal an error
    print("Error: failed to convert '" + fileName + "'.")

'''
get_next_line()
Gets the next line of the file from the current position of the stream positional
marker, skipping all lines that are purely whitespace.
    PARAMETERS:
        - the file to be read
    RETURNS:
        - the next non-whitespace line in the file 
'''
def get_next_line(file):
    line = file.readline()
    while line.isspace():
        line = file.readline()
    return line

'''
add_article()
Processes the article information from a given file, and adds it to a Newsletter object
    PARAMETERS:
        - The newsletter object, to which the article will be added
        - the name of the file containing the article
    RETURNS:
        - nothing
'''
def add_article(newsletter, filename):
    try:
        #Open the file in UTF-8 format
        article_file = open(filename, encoding = "utf-8-sig")
        
        #The first non-whitespace line of the file is taken to be the 
        #intended section of the article. It is 
        #stripped of leading and trailing whitespace
        section = get_next_line(article_file).rstrip()
        
        #The second non-whitespace line of the file is taken to be the 
        #intended title of the article
        title = get_next_line(article_file).rstrip()
        
    #If opening the file in UTF-8 was unsuccessful, try converting it to  UTF-8
    #and then re-extracting the article information
    except UnicodeDecodeError:
        article_file.close()
        convert_to_UTF8(filename)
        article_file = open(filename, encoding = "utf-8-sig", newline = "\n")
        section = get_next_line(article_file).rstrip()
        title = get_next_line(article_file).rstrip()
    finally:   
        #Initialise the variable for the article text
        text = ""
        
        #Add the text from the text file into the Newsletter object,
        #skipping leading empty lines (that is, all empty lines before the first
        #non-whitespace line)
        for line in article_file.readlines():
            if line != "\n" or len(text) > 0:
                text += line
        article_file.close()
    
    #If any of the required fields are empty, skip adding the article
    if "" not in [section, title, text]:
        newsletter.add_article(section, title, text)

'''
format_links_to_html
Goes through the texts of a Newsletter object, and formats all the url-links
it finds to html-form. It also wraps all the links, which match pre-specified patterns,
in an icon image as determined in the newsletter object.
    PARAMETERS:
        - The Newsletter object containing the articles
    RETURNS:
        - nothing
'''
def format_links_to_html(newsletter):
    #apply formatting to all the articles, including the intro and outro articles
    for article in [newsletter.get_intro()] + newsletter.get_articles() + [newsletter.get_outro()]:
        #Format all the url-links in the text to html-links with <a>-tags
        article.set_text(re.sub(r"((http:|https:)//[^ \s\<]*[^ \s\<,\.!:\?\)])", \
                                r'<a href="\1" target="_blank">\1</a>', \
                                article.get_text(), re.M|re.I))
        article.set_text(re.sub(r"([^/])(www\.[^ \s\<]*[^ \s\<,\.!:\?\)])", \
                                r'\1<a href="http://\2" target="_blank">\2</a>', \
                                article.get_text(), re.M|re.I))

        #Format the newlines into html-form 
        article.set_text(article.get_text().replace("\n", "\n<br/>"))
        
        #Replace certain identified links with pictures.
        icons = newsletter.get_icons()
        for target in icons:
            article.set_text(re.sub(r'>([^ \>\s\<]*' + target + r'[^ \s\<]*[^ \<,\.])', \
                                    r'><img src="' + icons[target] + r'" alt="\1"/>', \
                                    article.get_text(), re.M|re.I))
    return

'''
remove_formatting()
Removes all html-formatting from the articles in a Newsletter object. This is used
before generating the plain text version to clean the articles of any code. By default, 
everything surrounded by <> -tags is removed, with a few exceptions for aesthetic reasons:
    - '<b>' and '</b>' tags are replaced with '*'
    - '<i>' and '</i>' tags are replaced with '/'
    - '<u>' and '</u>' tags are replaced with '_'
    - '<li>' tags are replaced with '-    '
    - html-images are replaced with the url-address of the image
    
All of these changes are applied both to the texts and titles of the articles
    PARAMETERS:
        - The Newsletter object containing the articles to be modified
    RETURNS:
        - a copy of the Newsletter object, with all the html formatting removed
'''
def remove_formatting(newsletter):
    
    temp_newsletter = newsletter.copy()
    
    #Remove text formatting from all the articles, including the intro and contact articles
    for article in [temp_newsletter.get_intro()] + temp_newsletter.get_articles() + [temp_newsletter.get_outro()]:
        #replace bold formatting
        article.set_text(re.sub(r'</?b>', '*', article.get_text()))
        article.set_title(re.sub(r'</?b>', '*', article.get_title()))
        
        #replace italisized formatting
        article.set_text(re.sub(r'</?i>', '/', article.get_text()))
        article.set_title(re.sub(r'</?i>', '/', article.get_title()))
        
        #replace underlined formatting
        article.set_text(re.sub(r'</?u>', '_', article.get_text()))
        article.set_title(re.sub(r'</?u>', '_', article.get_title()))
        
        #replace list formatting
        article.set_text(re.sub(r'<li>', '-    ', article.get_text()))
        article.set_title(re.sub(r'<li>', '-    ', article.get_title()))
        
        #replace images with urls
        article.set_text(re.sub(r'<img [^"]*"[^"]*"\s*alt\s*=\s*"([^"]*)"\s*/*>', r'\1', article.get_text()))
        article.set_title(re.sub(r'<img [^"]*"[^"]*"\s*alt\s*=\s*"([^"]*)"\s*/*>', r'\1', article.get_title()))
        
        #remove everything else surrounded by <> -tags
        article.set_text(re.sub(r'<[^>]*>', "", article.get_text()))
        article.set_title(re.sub(r'<[^>]*>', "", article.get_title()))
    return temp_newsletter

'''
generate_soup()
This function generates the html-template on which the articles are finally layed
out, using the open-source BeautifulSoup library (version 4).
    PARAMETERS:
        - the Newsletter object, which contains information about the html
          background color, different article sections and such.
        - the template type, as a string. The default for this is "MAIL", 
          which means that the template will be a fixed width of 530px, and include
          the banner image plus intro text. Otherwise, the function will generate
          a template intended for web viewing. It will have a fixed width of 100%, 
          while omitting the banner and the intro text.
    RETURNS:
        - the html template, as a string
'''
def generate_soup(newsletter, template_type="MAIL"):
    #Initialize the BeautifulSoup object
    soup = BeautifulSoup()
    
    #Add tags to the beginning
    soup.append(soup.new_tag("html"))
    soup.html.append(soup.new_tag("head"))
    soup.head.append(soup.new_tag("meta", content="text/html; charset=utf-8" ))
    #soup.head.append(soup.new_tag("link", rel="stylesheet", href="https://fonts.googleapis.com/css?family=Open+Sans"))
    soup.head.meta["http-equiv"] = "Content-Type"
    
    #Add title
    soup.head.append(soup.new_tag("title"))
    soup.title.string = "InkuMail Newsletter"
    
    #Add body-tag
    soup.html.append(soup.new_tag("body", \
                                  bgcolor = newsletter.get_color("background"), \
                                  style = "margin: 0; padding: 0;"))
    
    if template_type == "MAIL":
        soup.body.append(Comment(" the large table which holds everything "))
        soup.body.append(soup.new_tag("table", \
                                  align = "center", \
                                  cellpadding = "0", \
                                  cellspacing = "0", \
                                  border = "0", \
                                  style = "width: 100%; max-width: 530px;", \
                                  bgcolor = newsletter.get_color("foreground"), \
                                  **{'class':'Content'}))
        soup.table.append(soup.new_tag("tr"))
        soup.table.append(soup.new_tag("td"))
        soup.td.append(Comment(" table that holds the large column with all the content "))
        soup.td.append(soup.new_tag("table", align = "center", \
                                 bgcolor = newsletter.get_color("foreground"), \
                                 style = "table-layout: fixed; width: 100%; border: 1px solid #e1e1e1 ; max-width: 530px; border-collapse: collapse;"))
        column = soup.table.table
        column.append(soup.new_tag("tr"))
        column.tr.append(soup.new_tag("td"))
        column.td.append(Comment(" BANNER image goes here "))

        column.append(soup.new_tag("tr"))
        intro = column.find_all("tr")[-1]
        intro.append(soup.new_tag("td", \
                              align = "center", \
                              style = "padding: 0 0 0 0;"))
        intro.td.append(soup.new_tag("table", \
                                 style = "width: 100%; align: left; max-width: 540px;", \
                                 bgcolor = newsletter.get_color("foreground")))
        intro.table.append(soup.new_tag("tr"))
        intro.table.tr.append(soup.new_tag("td", \
                                       style = "font-family: 'Trebuchet MS', Arial, sans-serif; font-size: 30px; font-weight: bold; color: " + newsletter.get_intro().get_color() + "; padding: 15px;"))
        intro.table.td.append(Comment(" INTRO text goes here "))
    
        soup.table.table.append(soup.new_tag("tr"))
        title_list = soup.table.table.find_all("tr")[-1]
        title_list.append(soup.new_tag("td"))
        title_list.td.append(soup.new_tag("table", \
                                      style = "table-layout: fixed; width = 100%; max-width: 530px;", \
                                      align = "left", \
                                      bgcolor = newsletter.get_color("foreground")))
    else:
        soup.body.append(soup.new_tag("table"))
        column = soup.table;
        column.append(soup.new_tag("tr"))
        column.append(soup.new_tag("td"))
        title_list = column.find_all("tr")[-1]
        title_list.append(soup.new_tag("td"))
        title_list.td.append(soup.new_tag("table", \
                                      style = "table-layout: fixed; width = 100%;", \
                                      align = "left", \
                                      bgcolor = newsletter.get_color("foreground")))
    title_list.table.append(soup.new_tag("a"))
    title_list.a["name"] = "beginning"
    for section in newsletter.get_sections():
        if section not in ["INTRO", "OUTRO"]:
            title_list.table.append(soup.new_tag("tr"))
            title_list.find_all("tr")[-1].append(soup.new_tag("td"))
            title_list.find_all("td")[-1].append(Comment(" " + section + " titles go here "))
    
    column.append(soup.new_tag("tr"))
    articles = column.find_all("tr")[-1]
    articles.append(soup.new_tag("td"))
    if template_type == "MAIL":
        articles.td.append(soup.new_tag("table", \
                                    bgcolor = newsletter.get_color("foreground"), \
                                    width = "100%", \
                                    style = "table-layout: fixed; font-family: 'Trebuchet MS', Arial, sans-serif; max-width = 530px; font-size: 14px;"))
    else:
        articles.td.append(soup.new_tag("table", \
                                    bgcolor = newsletter.get_color("foreground"), \
                                    width = "100%", \
                                    style = "table-layout: fixed; font-family: 'Trebuchet MS', Arial, sans-serif; font-size: 14px;"))
    for section in newsletter.get_sections():
        articles.table.append(Comment(" " + section + " articles go here "))
    articles.table.append(Comment(" OUTRO text goes here "))
    
    return(soup.prettify())

'''
generate_html_version()
This function inserts the articles from a Newsletter object into an html-template.
    PARAMETERS:
		- the html template string, as returned by the generate_soup() -function
        - the Newsletter object, which contains information about the html
          background color, different article sections and such.
        - the template type, as a string. The default for this is "MAIL", 
          which means that the template will be a fixed width, and include
          the banner image plus intro text. Otherwise, the function will generate
          a template intended for web viewing. It will have a fixed width, 
          while omitting the banner and the intro text.
    RETURNS:
        - A new string, where the images, and text from inside the newsletter object
          have been added to the html template

'''
def generate_html_version(html_template, newsletter, template_type="MAIL"):
    html_version = html_template[:]
    current_section = ""
    intro = newsletter.get_intro()
    outro = newsletter.get_outro()
    articles =  newsletter.get_articles()
    
    #Insert the banner image
    for lineNo, line in enumerate(html_version):
        if lineNo == 1:
            html_version.insert(lineNo,"<!-- Generated with InkuMail " + \
                                "(author Timo Vehvilainen) on date: " + \
                                str(datetime.datetime.now()) + "-->\n")
        if ("BANNER image goes here") in line:
            html_version.insert(lineNo,
"""\t\t\t\t\t\t\t\t\t         <img src=\""""+newsletter.get_banner()+"""\" width = 530 style="width: 100%; """+ \
                                """max-width: 530 px;" alt=""/>
""")
            break
        
    #Insert the title and the intro
    for lineNo, line in enumerate(html_version):
        if ("INTRO text goes here") in line:
            html_version.insert(lineNo, 
"""\t\t\t\t                    <tr>
\t\t\t\t                        <td style="font-family: 'Trebuchet MS', Arial, sans-serif; font-size: 30px; """+  \
                                    """font-weight: bold; color: #"""+intro.get_color()+"""; padding: 15px;">
\t\t\t\t                            """+intro.get_title()+"""
\t\t\t\t                        </td>
\t\t\t\t                    </tr>
\t\t\t\t                    <tr>
\t\t\t\t                        <td style="font-family: 'Trebuchet MS', Arial, sans-serif; font-size: 14px; """+  \
                                    """color: #"""+newsletter.get_color("text")+"""; padding: 10px;" >
\t\t\t\t                            <p>
\t\t\t\t                                """+intro.get_text()+"""
\t\t\t\t                            </p>
\t\t\t\t                        </td>
\t\t\t\t                    </tr>
""")
            break
    #Iterate through the articles
    for articleNo, article in enumerate(articles):
        #Insert the title to the index
        for lineNo, line in enumerate(html_version):
            if (article.get_section() in line) and ("titles go here" in line):
                #Between the sections, insert a color banner
                if article.get_section() != current_section:
                    current_section = article.get_section()
                    html_version.insert(lineNo,
"""\t\t\t\t\t\t\t\t            <table style="color:"""+newsletter.get_color("section_text", current_section)+"""; font-family: 'Trebuchet MS', Arial, sans-serif; font-size:14px; height: 5px; width: 30%;" align="left" """+\
                                """bgcolor=\""""+article.get_color()+"""\">
\t\t\t\t\t\t\t\t                <tr> <td>"""+article.get_section()+""" </td> </tr>
\t\t\t\t\t\t\t\t            </table>
\t\t\t\t\t\t\t\t        </td>
\t\t\t\t\t\t\t\t    </tr>
\t\t\t\t\t\t\t\t    <tr>
\t\t\t\t\t\t\t\t        <td style="font-family: 'Trebuchet MS', Arial, sans-serif; font-size:14px;"""+\
                        """color: black; padding: 10px 0 10px 30px;">""")
                    lineNo += 1
                #Then insert the title
                html_version.insert(lineNo, """
\t\t\t\t\t\t\t\t\t\t    <a style="color:#"""+newsletter.get_color("link")+"""; text-decoration:none; padding: 0 0 5px 0;" """+  \
                            """href="#title"""+str(articleNo + 1)+"""\">
\t\t\t\t\t\t\t\t\t\t\t    """ + str(articleNo + 1) + """. """ + article.get_title() + """
\t\t\t\t                            </a><br/>""")
                break
        
        #Insert the article
        for lineNo in range(len(html_version)):
                if (article.get_section() + " articles go here") in html_version[lineNo]:
                    #insert the banner and article title
                    html_version.insert(lineNo, 
"""\t\t\t\t\t\t\t        <tr>
\t\t\t\t\t\t\t            <td>
\t\t\t\t\t\t\t                <table style=" height: 5px; width: 90%;" """ +\
							""" align="left" bgcolor=\""""+article.get_color()+"""\">
\t\t\t\t\t\t\t                    <tr> 
\t\t\t\t\t\t\t                        <td> 
\t\t\t\t\t\t\t							<a name = "title"""+str(articleNo + 1)+"""\"> </a>
\t\t\t\t\t\t\t                        </td> 
\t\t\t\t\t\t\t                    </tr>
\t\t\t\t\t\t\t                </table>
\t\t\t\t\t\t\t            </td>
\t\t\t\t\t\t\t        </tr>
\t\t\t\t\t\t\t        <tr>
\t\t\t\t\t\t\t            <td style="color: #"""+newsletter.get_color("text")+"""; word-wrap: break-word; max-width: 530px;">
\t\t\t\t\t\t\t                <div style="padding: 10px 0 0 30px;">
\t\t\t\t\t\t\t                        <b>
\t\t\t\t\t\t\t                            """ + str(articleNo + 1) + """. """ + article.get_title() + """
\t\t\t\t\t\t\t                        </b><br/>
\t\t\t\t\t\t\t                </div>
\t\t\t\t\t\t\t                <div>
\t\t\t\t\t\t\t                    <p>
""")
                    lineNo += 1
                    
                    #insert the article text and a link to the beginning
                    html_version.insert(lineNo, article.get_text() + 
"""\t\t\t\t\t\t\t                    </p>
\t\t\t\t\t\t\t                </div>
\t\t\t\t\t\t\t                <p style = "width: 100%; max-width: 530px;" align="right">
\t\t\t\t\t\t\t                    <a style="color:#"""+newsletter.get_color("link")+ \
                                    """; text-decoration:none;" href="#beginning">
\t\t\t\t\t\t\t                        <img src=\""""+ newsletter.get_top_icon() +"""\" alt="Top"/>
\t\t\t\t\t\t\t                    </a> 
\t\t\t\t\t\t\t                </p>
\t\t\t\t\t\t\t            </td>
\t\t\t\t\t\t\t        </tr>
""")
                    break
            
    #Insert outro
    for lineNo, line in enumerate(html_version):
        if ("OUTRO text goes here") in line:
            html_version.insert(lineNo, 
"""\t\t\t\t\t\t\t\t    <tr>
\t\t\t\t\t\t\t\t       <td>
\t\t\t\t\t\t\t\t           <table width="100%" align="left" bgcolor=\""""+\
                                    outro.get_color()+"""\">
\t\t\t\t\t\t\t\t              <tr> <td> </td> </tr>
\t\t\t\t\t\t\t\t           </table>
\t\t\t\t\t\t\t\t       </td>
\t\t\t\t\t\t\t\t    </tr>                                    
\t\t\t\t\t\t\t\t    <tr>
\t\t\t\t\t\t\t\t        <table width="100%" align="left">
\t\t\t\t\t\t\t\t            <tr>
\t\t\t\t\t\t\t\t                <td style="color: #"""+ newsletter.get_color("text") + """; font-family: 'Trebuchet MS', Arial, sans-serif; font-size:14px;">
\t\t\t\t\t\t\t\t                    """ + outro.get_text() + """
\t\t\t\t\t\t\t\t                </td>
\t\t\t\t\t\t\t\t           </tr>
\t\t\t\t\t\t\t\t        </table>""")
            break
    #return a string version of the list of lines
    return "".join(html_version)
               
'''
generate_plain_text_version()
This function generates a plain text version of a Newsletter object, by
generating a version without any hmtl-formatting.
    PARAMETERS:
        - the nNewsletter object to be converted to plain text
    RETURNS:
        - the plain text version of the Newsletter object, as a string
''' 
def generate_plain_text_version(temp_newsletter):
    
    #Create a copy of the given object to work with, with all formatting removed
    newsletter = remove_formatting(temp_newsletter)
    
    intro = newsletter.get_intro()
    outro = newsletter.get_outro()
    articles =  newsletter.get_articles()
    
    #Prepare the dividers for the plain text version
    starline = ("*" * 40)                               #helper variable
    index_divider = "\n\n" + starline
    article_divider = "\n\n"+(starline * 2) + "\n\n"
    outro_divider = (("\n" + starline) * 3) + "\n" 
    
    #insert the title and intro text separately
    text = "\t"
    text += intro.get_title() + "\n\n" + intro.get_text() + index_divider
    
    #Insert the index of titles
    current_section = ""
    for articleNo, article in enumerate(articles):
        #place an empty line where the section of the articles changes
        if article.get_section() != current_section:
            current_section  = article.get_section()
            text += "\n\n" + current_section
        text += "\n\t" + str(articleNo + 1) + ". " + article.get_title()

    #Insert the articles into the text, separated by dividers
    for articleNo, article in enumerate(articles):
        text += article_divider + "\t" + str(articleNo + 1) + ". " + article.get_title() +\
        "\n\n" + article.get_text()
    
    #Lastly, insert the last divider and outro
    text += outro_divider
    text += outro.get_text()
    
    return text
    
'''
generate_MIME_version()
This function makes a MIME (Multi-purpose Internet Mail Extension) file, using
the email python library. This file combines the html and plain text versions 
of the newsletter into file, which can then be sent as an email.
    PARAMETERS:
        - The Newsletter object
        - The html-version of the Newsletter object, as a string
        - the plain text version of the Newsletter object, as a string
    RETURNS:
        - A MIMEMultipart object, containing both the html and plain text versions
'''
def generate_MIME_version(newsletter, html_version, plain_text_version):
    
    #Get the sender and reccipient addresses
    from_address = newsletter.get_address("from")
    to_address = newsletter.get_address("to")
    
    #Prepare the email subject
    subject = newsletter.get_intro().get_title()
    #Remove any possible html-formatting from the subject line
    subject = re.sub(r'<[^>]*>', "", subject)
    
    #The subject will have varying prefixes, depending on which email lists
    #it will be sent to. These have to be added manually, since the ayy
    #mailing lists for some reason don't add it to the MIME file
    
    #TODO: do this smarter, with XML-files and in the sending phase 
    subject_prefix = ""
    prefixes = {"inkubio@list.ayy.fi": "[Inkubio] ", \
                "hallitus@inkubio.fi": "[Inkubio-hal] ", \
                "fuksit@inkubio.fi": "[Inkubio-fuksit] ", \
                "international@inkubio.fi": "[Inkubio-international] ", \
                "tiedotus@inkubio.fi": "[Inkubio-tiedotus] ", \
                "isot@inkubio.fi": "[Inkubio-isot] "}
    for prefix in prefixes:
        if prefix in to_address:
            subject_prefix += prefixes[prefix]
            
    #Construct the MIMEMultipart object
    msg = MIMEMultipart('alternative')
    msg.set_charset('utf-8') 
    
    msg['Subject'] = Header(subject_prefix + subject, 'utf-8')
    #any spaces are removed from the sender address, in case any were added accidentally
    msg['From'] = from_address.replace(" ", "")
    #same is done recipient addresses. Additionally, half-colons are replaced with
    #commas, making both of them valid separators when inputting.
    msg['To'] = to_address.replace(" ", "").replace(";", ",")
    
    #Attach the plain text and html versions to the eml-file
    msg.attach(MIMEText(plain_text_version.encode('utf-8'), 'plain', 'utf-8'))
    msg.attach(MIMEText(html_version.encode('utf-8'), 'html', 'utf-8'))
    
    return msg
'''
bold_new_titles()
This function boldens all the titles in the newsletter for articles 
which have been modified since the last newsletter archive-folder was created (ie.
since the last newsletter was sent). 
This function doesn't actually modify the files, but only modifies the Newsletter-object.
It then compiles the newsletter, so that the files in the active-folder will contain the
boldened versions for previewing & sending.
    PARAMETERS:
        - A Newsletter object
    RETURNS:
        - nothing
'''

def bold_new_titles(newsletter):
    parent_path = os.getcwd()
    archive_path = parent_path + "/" + newsletter.get_newsletter_type() + "/archive/" + \
                    str(get_current_year())
    article_path = parent_path + "/" + get_article_folderpath(newsletter.get_newsletter_type())[:-1]
                    
    archive_dirs = os.listdir(archive_path)
    os.chdir(archive_path)
    latest_send_date = max(map(os.path.getmtime, archive_dirs))
    os.chdir(article_path)
    article_files = filter((lambda x: x.endswith(".txt")), os.listdir(article_path))
    
    for file in article_files:
        if os.path.getmtime(file) > latest_send_date:
            with open(file, 'r') as article:
                section = get_next_line(article)
                title = get_next_line(article)[:-1]
            for articles in newsletter.get_articles():
                if articles.get_title() == title:
                    articles.set_title("<b>" + title + "</b>")
    os.chdir(parent_path)
    
'''
unbold_all_titles()
This functions removes any bloding from the titles of all the articles. In other words,
it removes any <b> & </b> -tags around titles, as well as "*" -signs. It doesn't modify
the actual article .txt-files, but only modifies the Newsletter object. It then compiles
the newsletter.
    PARAMETERS: 
        - a Newsletter object
    RETURNS:
        - nothing
'''

def unbold_all_titles(newsletter):
    for article in newsletter.get_articles():
        if article.get_title().startswith("<b>") and article.get_title().endswith("</b>"):
            article.set_title(article.get_title()[3:-4])
        if article.get_title()[0] == article.get_title()[-1] == '*':
            article.set_title(article.get_title()[1:-1])

'''
get_current_week()
This function is obsolete now. It was used in a previous version of InkuMail, 
where the newsletter titles and email subjects were generated automatically.
This functionality was discontinued, for the ability to send newsletters with
varying formats of titles.
    PARAMETERS: 
        - none
    RETURNS:
        - the number of the current week
'''

def get_current_week():
    current_week = datetime.date.isocalendar(datetime.date.today())[1] + 1
    
    #As far as the newsletter is concerned, a new week starts at Tuesday
    #so if it is still Monday, compensate and remove 1
    if datetime.date.isoweekday(datetime.date.today()) == 1:
        current_week -= 1
        
    return current_week

'''
get_current_year()
This function is used in the generation of the folderpath for newsletter archives
    PARAMETERS: 
        - none
    RETURNS:
        - the current year, as an integer
'''
def get_current_year():
    return datetime.date.isocalendar(datetime.date.today())[0]


'''
get_archive_folderpath()
This function generates a folderpath for the archive of a given newsletter
    PARAMETERS:
        - the Newsletter object to be archived
    RETURNS:
        - the folderpath to the correct archive file, as a string
'''
def get_archive_folderpath(newsletter):
    #Each individual newsletter is stored into folder carrying its intro title
    subfolder_name = newsletter.get_intro().get_title()
    
    #Replacing forbidden foldername characters with '_'
    forbidden_characters = ['~','"','#','%','&','*',':','<','>',\
                            '?','/','\\','{','|','}']
    for char in forbidden_characters:
        subfolder_name = subfolder_name.replace(char, '_')
        
    #generate full folderpath
    foldername = "/" + newsletter.get_newsletter_type() + "/archive/" + \
                 str(get_current_year()) + "/" + subfolder_name
    return foldername
                 
'''
get_active_folderpath()
generates the folderpath for the 'active' newsletter files. That is, for the 
files that have been most recently compiled.
    PARAMETERS:
        - the Newsletter object, for which the folderpath is generated
    RETURNS:
        - the folderpath for the active files, as a string
'''
def get_active_folderpath(newsletter_type): 
    foldername = "/" + newsletter_type + "/active/"
    return foldername

'''
get_article_folderpath()
generates the folderpath for the articles of a given Newsletter object. This is 
the folder where all the .txt-article files are stored.
    PARAMETERS:
        - the Newsletter object, for which the fodlerpath is generated
    RETURNS:
        - the folderpath for the article files, as a string
'''
def get_article_folderpath(newsletter_type):
    foldername = "/" + newsletter_type + "/articles/"
    return foldername

