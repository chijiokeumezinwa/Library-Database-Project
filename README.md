# Cloud-Hosted Library Database Project
The goal of the project was to build a Flask application hosted on an AWS EC2 instance that is served by Gunicorn and proxied by Nginx. 

## Features of app:
  * **Book Availability:** Real-time checking of book availability.
  * **Checkout/Return System:** Functionality for users to check out and return books.
  * **User Authentication:** Secure login/logout for users and administrators.
  * **Admin Privileges:** Separate functionalities for administrative users

## Features of database and backend:
  * **MySQL database schema** was used to model the relational tables needed to store information
  * **AWS EC2** was the cloud infrastructure used to host this application
  * **Nginx** was used as reverse proxy server
  * **Gunicorn** was used as application server

## Technologies used:
  * **Cloud Platform**: AWS (EC2)

  * **Databases**: MySQL

  * **Web/App Servers**: Nginx, Gunicorn

  * **Programming/Scripting**: Python (Flask, Boto3), Shell Scripting

  * **Version Control**: Git 

# How to Run
**Prerequisites:**

  * An AWS EC2 instance (Ubuntu 22.04 LTS or similar) up and running.
  * SSH access to the EC2 instance (your `.pem` key).
  * A domain name pointing to your EC2 instance's Public IPv4 address via DNS (e.g., A record).

-----

**Steps:**

1.  **Connect to EC2 & Initial Setup:**

    ```bash
    ssh -i /path/to/your/key.pem ubuntu@your-ec2-public-ip
    sudo apt update && sudo apt upgrade -y
    sudo apt install python3-pip python3-venv nginx mysql-server -y
    ```

      * **AWS Security Group:** Ensure your EC2 instance's security group allows inbound traffic on **ports 22 (SSH), 80 (HTTP), and 443 (HTTPS)** from `0.0.0.0/0`.

2.  **Clone Your Flask App & Set Up Virtual Environment:**

    ```bash
    mkdir ~/projects && cd ~/projects
    git clone https://github.com/your-repo/Library-Database-Project.git # Replace with your actual repo URL
    cd Library-Database-Project
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt # Ensure you have a requirements.txt file
    ```

3.  **Configure MySQL Database:**

    ```bash
    sudo mysql_secure_installation # Follow prompts: set root password, remove test users etc.
    sudo mysql -u root -p
    ```

    (Enter the root password you just set)

    ```sql
    CREATE DATABASE library_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
    CREATE USER 'flask_user'@'localhost' IDENTIFIED BY 'your_secure_db_password'; # Set a strong password
    GRANT ALL PRIVILEGES ON library_db.* TO 'flask_user'@'localhost';
    FLUSH PRIVILEGES;
    EXIT;
    ```

      * **Import Schema/Data:** If you have an `init_db.sql` or `backup.sql`:
        ```bash
        mysql -u flask_user -p library_db < your_schema_file.sql
        ```

4.  **Configure Flask App Database URI & Test:**

      * Create a `.env` file in your `Library-Database-Project` directory (or set environment variables directly):
        ```bash
        nano .env
        ```
        Add:
        ```
        SQLALCHEMY_DATABASE_URI="mysql+pymysql://flask_user:your_secure_db_password@localhost/library_db?charset=utf8mb4"
        SECRET_KEY="your_flask_secret_key" # Replace with a strong, random key
        ```
        (Save & exit nano: Ctrl+X, Y, Enter)
      * Test your Flask app locally (stop with Ctrl+C):
        ```bash
        flask run
        # Test connecting to http://localhost:5000 in a new SSH tunnel:
        # ssh -i /path/to/your/key.pem -L 5000:localhost:5000 ubuntu@your-ec2-public-ip
        ```
      * Deactivate virtual environment: `deactivate`

5.  **Set Up Gunicorn Systemd Service:**

    ```bash
    sudo nano /etc/systemd/system/library_app.service
    ```

    Add this content (adjust `WorkingDirectory` and `ExecStart` paths if different):

    ```ini
    [Unit]
    Description=Gunicorn instance to serve library_app
    After=network.target

    [Service]
    User=ubuntu
    Group=www-data
    WorkingDirectory=/home/ubuntu/projects/Library-Database-Project
    ExecStart=/home/ubuntu/projects/Library-Database-Project/venv/bin/gunicorn --workers 3 --bind unix:/home/ubuntu/projects/Library-Database-Project/library_app.sock -m 007 wsgi:app
    # Note: wsgi:app assumes your Flask app instance is named 'app' in 'wsgi.py' or 'app.py'
    # If your Flask app is in app.py and app=Flask(__name__), use app:app
    # ExecStart=/home/ubuntu/projects/Library-Database-Project/venv/bin/gunicorn --workers 3 --bind unix:/home/ubuntu/projects/Library-Database-Project/library_app.sock -m 007 app:app
    Restart=always

    [Install]
    WantedBy=multi-user.target
    ```

    (Save & exit nano)

    ```bash
    sudo systemctl daemon-reload
    sudo systemctl start library_app
    sudo systemctl enable library_app
    sudo systemctl status library_app # Check that it's 'active (running)'
    ```

6.  **Configure Nginx as Reverse Proxy:**

    ```bash
    sudo nano /etc/nginx/sites-available/library_app
    ```

    Add this content (replace `your-duckdns-domain.org` with `library-app012.duckdns.org`):

    ```nginx
    server {
        listen 80;
        server_name your-duckdns-domain.org www.your-duckdns-domain.org; # Add your actual domain(s) here

        location / {
            include proxy_params;
            proxy_pass http://unix:/home/ubuntu/projects/Library-Database-Project/library_app.sock;
            # Ensure this path matches the socket path in your Gunicorn service file
        }

        # Optional: Serve static files directly via Nginx (uncomment and adjust path)
        # location /static/ {
        #     alias /home/ubuntu/projects/Library-Database-Project/static/;
        # }
    }
    ```

    (Save & exit nano)

    ```bash
    sudo ln -s /etc/nginx/sites-available/library_app /etc/nginx/sites-enabled/
    sudo rm /etc/nginx/sites-enabled/default # Remove default Nginx config
    sudo nginx -t # Test Nginx configuration for errors
    sudo systemctl reload nginx
    ```

      * **Test HTTP:** Browse to `http://your-duckdns-domain.org`. Your app should now be visible.

7.  **Enable HTTPS with Let's Encrypt (Certbot):**

    ```bash
    sudo snap install core
    sudo snap refresh core
    sudo apt-get remove certbot # Remove any old apt version first
    sudo snap install --classic certbot
    sudo ln -s /snap/bin/certbot /usr/bin/certbot
    ```

      * **Get Certificate & Auto-Configure Nginx:**
        ```bash
        sudo certbot --nginx -d library-app012.duckdns.org -d www.library-app012.duckdns.org
        ```
        (Follow prompts: provide email, agree to terms, choose to redirect HTTP to HTTPS - option `2`)
      * **Reload Nginx (if not done automatically):**
        ```bash
        sudo nginx -t
        sudo systemctl reload nginx
        ```
      * **Test HTTPS:** Browse to `https://library-app012.duckdns.org`. You should see a secure padlock.

-----

**Ongoing Management:**

  * **To restart app after code changes:** `sudo systemctl restart library_app`
  * **To check app logs:** `sudo journalctl -u library_app.service -f`
  * **Certificates auto-renew.** You can test renewal with `sudo certbot renew --dry-run`.