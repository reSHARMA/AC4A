import logging
from datetime import datetime
from .base_agent import BaseAgent
from ..web_input import web_input_func
from src.policy_system.api_annotation import APIAnnotationBase
from src.utils.attribute_tree import AttributeTree
from src.utils.dummy_data import generate_dummy_data
from config import WILDCARD

# Set up logging
logger = logging.getLogger(__name__)

class WebBrowserAPIAnnotation(APIAnnotationBase):
    attributes_schema = {
        'WebBrowser:ParentDomain': {
            'description': 'The main domain of the website',
            'examples': ['google.com', 'amazon.com', 'facebook.com']
        }, 
        'WebBrowser:ChildDomain': {
            'description': 'The subdomain of the website',
            'examples': ['mail.google.com', 'images.google.com', 'maps.google.com']
        },
        'WebBrowser:Path': {
            'description': 'The path of the website',
            'examples': ['/mail', '/images', '/maps']
        },
        'WebBrowser:QueryParams': {
            'description': 'The query parameters of the website',
            'examples': ['?q=python', '?q=java', '?q=javascript']
        },
        'WebBrowser:URL': {
            'description': 'The full URL of the website',
            'examples': ['https://www.google.com/mail?q=read_email', 'https://www.amazon.com/search?q=books', 'https://www.facebook.com/profile?id=1234567890']
        },
        'WebBrowser:Cookies': {
            'description': 'The cookies of the website',
            'examples': ['JSESSIONID=1234567890', 'PHPSESSID=1234567890', 'csrftoken=1234567890']
        },
        'WebBrowser:CookieName': {
            'description': 'The name of the cookie',
            'examples': ['JSESSIONID', 'PHPSESSID', 'csrftoken']
        }
    }
    def __init__(self):
        super().__init__("WebBrowser", {
            'granular_data': [
                AttributeTree(f'WebBrowser:URL', [
                    AttributeTree(f'WebBrowser:ParentDomain'),
                    AttributeTree(f'WebBrowser:ChildDomain'),
                    AttributeTree(f'WebBrowser:Path'),
                    AttributeTree(f'WebBrowser:QueryParams')
                ]),
                AttributeTree(f'WebBrowser:Cookies', [
                    AttributeTree(f'WebBrowser:CookieName')
                ])
            ],
            'data_access': [
                AttributeTree('Read'),
                AttributeTree('Write')
            ],
            'position': [
                AttributeTree('Previous', [AttributeTree('Current')]),
                AttributeTree('Next', [AttributeTree('Current')])
            ]
        }, self.attributes_schema)
    def get_hierarchy(self, endpoint_name, kwargs, use_wildcard):
        api_to_granular_data = {
            'get_attributes': f'{self.namespace}:URL(*)',
            'get_attributes_schema': f'{self.namespace}:URL(*)',
            'post_request': f'{self.namespace}:URL({kwargs.get("url", "*")})',
            'get_request': f'{self.namespace}:URL({kwargs.get("url", "*")})',
            'put_request': f'{self.namespace}:URL({kwargs.get("url", "*")})',
            'delete_request': f'{self.namespace}:URL({kwargs.get("url", "*")})',
            'add_cookie': f'{self.namespace}:Cookies({kwargs.get("cookie_name", "*")})',
            'remove_cookie': f'{self.namespace}:Cookies({kwargs.get("cookie_name", "*")})',
            'update_cookie': f'{self.namespace}:Cookies({kwargs.get("cookie_name", "*")})',
            'get_all_cookies': f'{self.namespace}:Cookies(*)'
        }
        return api_to_granular_data.get(endpoint_name, f'{self.namespace}:URL(*)')

    def get_access_level(self, endpoint_name):
        return 'Write' if 'add' in endpoint_name or 'remove' in endpoint_name or 'update' in endpoint_name else 'Read'

    def get_time_period(self, start_time, end_time, use_wildcard):
        return "Current"

    def generate_attributes(self, kwargs, endpoint_name, wildcard):
        start_time = datetime.now()
        end_time = start_time  # For wallet operations, the time period is typically immediate
        granular_data = self.get_hierarchy(endpoint_name, kwargs, wildcard)
        data_access = self.get_access_level(endpoint_name)
        position = self.get_time_period(start_time, end_time, wildcard)
        
        return {
            'granular_data': granular_data,
            'data_access': data_access,
            'position': position
        }

class WebBrowserAPI:
    def __init__(self, policy_system):
        self.annotation = WebBrowserAPIAnnotation()
        self.policy_system = policy_system

    @WebBrowserAPIAnnotation.export
    def get_attributes(self):
        return self.annotation.attributes

    @WebBrowserAPIAnnotation.schema
    def get_attributes_schema(self):
        return self.annotation.attributes_schema

    @WebBrowserAPIAnnotation.annotate
    def post_request(self, *args, **kwargs):
        return generate_dummy_data(
            api_endpoint="post_request: post a request to the given URL with the given data and also return a cookie if any",
            **kwargs
        )

    @WebBrowserAPIAnnotation.annotate
    def get_request(self, *args, **kwargs):
        return generate_dummy_data(
            api_endpoint="get_request: get a request from the given URL, if it is a homepage which is a login page, clearly output that email and password are required. Also return a cookie if any",
            **kwargs
        )

    @WebBrowserAPIAnnotation.annotate
    def put_request(self, *args, **kwargs):
        return generate_dummy_data(
            api_endpoint="put_request: put a request to the given URL with the given data and also return a cookie if any",
            **kwargs
        )

    @WebBrowserAPIAnnotation.annotate
    def add_cookie(self, *args, **kwargs):
        return generate_dummy_data(
            api_endpoint="add_cookie: add a cookie to the given URL",
            **kwargs
        )

    @WebBrowserAPIAnnotation.annotate
    def remove_cookie(self, *args, **kwargs):
        return generate_dummy_data(
            api_endpoint="remove_cookie: remove a cookie from the given URL",
            **kwargs
        )

    @WebBrowserAPIAnnotation.annotate
    def get_cookies(self, *args, **kwargs):
        return generate_dummy_data(
            api_endpoint="get_cookies: get all the cookies from the given URL",
            **kwargs
        )

    @WebBrowserAPIAnnotation.annotate
    def update_cookie(self, *args, **kwargs):
        return generate_dummy_data(
            api_endpoint="update_cookie: update a cookie from the given URL",
            **kwargs
        )

    @WebBrowserAPIAnnotation.annotate
    def get_all_cookies(self):
        return generate_dummy_data(
            api_endpoint="get_all_cookies: get all the cookies"
        )

class WebBrowserAgent(BaseAgent):
    """Web browser agent for managing web browser operations"""
    
    def __init__(self, model_client, policy_system):
        """
        Initialize the web browser agent
        
        Args:
            model_client: The model client to use
            policy_system: The policy system to use
        """
        system_message = """
        You are a web browser simulator agent. Use the tools provided to you to complete the task given to you. Start with reasoning about the task and then use the tools to complete the task. 
        Do not make up any data, especially for the cookies and credentials. 

        If you have a cookie for a website, use that cookie for all the requests to that website.
        If you get a cookie from a request, add it to the cookies.
        
        ## List of tools avaiable to you 
        [
            "post_request",
            "get_request",
            "put_request",
            "add_cookie",
            "remove_cookie",
            "get_cookies",
            "update_cookie",
            "get_all_cookies"
        ]

        ## Description of the tools available to you
        - post_request: post a request to the given URL with the given data
        - get_request: get a request from the given URL
        - put_request: put a request to the given URL with the given data
        - add_cookie: add a cookie to the given URL
        - remove_cookie: remove a cookie from the given URL
        - get_cookies: get all the cookies from the given URL
        - update_cookie: update a cookie from the given URL
        - get_all_cookies: get all the cookies

        Use the tool `post_request` to post a request to the given URL with the given data. The tool takes the following parameters:
        - url: The URL to post the request to, example "https://www.google.com".
        - data: The data to post to the given URL, example "{\"key\": \"value\"}".
        - cookies: The cookies to include in the request, example "{\"JSESSIONID\": \"1234567890\"}".
        Use the tool `get_request` to get a request from the given URL. The tool takes the following parameters:
        - url: The URL to get the request from, example "https://www.google.com".
        - cookies: The cookies to include in the request, example "{\"JSESSIONID\": \"1234567890\"}".
        Use the tool `put_request` to put a request to the given URL with the given data. The tool takes the following parameters:
        - url: The URL to put the request to, example "https://www.google.com".
        - data: The data to put to the given URL, example "{\"key\": \"value\"}".
        - cookies: The cookies to include in the request, example "{\"JSESSIONID\": \"1234567890\"}".

        Use the tool `get_all_cookies` to get all the cookies. The tool takes no parameters.

        Use the tool `add_cookie` to add a cookie to the given URL. The tool takes the following parameters:
        - cookie_name: The name of the cookie to add, example "JSESSIONID".
        - cookie_value: The value of the cookie to add, example "1234567890".
        - cookie_domain: The domain of the cookie to add, example "google.com".
        - cookie_path: The path of the cookie to add, example "/".
        - cookie_expiry: The expiry date of the cookie to add, example "01/26".

        Use the tool `remove_cookie` to remove a cookie from the given URL. The tool takes the following parameters:
        - cookie_name: The name of the cookie to remove, example "JSESSIONID".

        Use the tool `get_cookies` to get all the cookies from the given URL. The tool takes the following parameters:
        - url: The URL to get the cookies from, example "https://www.google.com".

        Use the tool `update_cookie` to update a cookie from the given URL. The tool takes the following parameters:
        - cookie_name: The name of the cookie to update, example "JSESSIONID".
        - cookie_value: The value of the cookie to update, example "1234567890".
        - cookie_domain: The domain of the cookie to update, example "google.com".
        - cookie_path: The path of the cookie to update, example "/".
        - cookie_expiry: The expiry date of the cookie to update, example "01/26".

        Carefully pick the tool to use based on the user request and you can use multiple tools if needed.
        Since you can simulate any website, try to fulfill the user request at your best.
        For permission or credentials, just output as text: fetch permission or fetch credentials for the specific service/user without calling any of the tools.

        Return "done" when you have completed your work.
        """
        
        policy_system.register_api(WebBrowserAPI)
        self.web_browser_api = WebBrowserAPI(policy_system)
        
        tools = [
            self.web_browser_post_request,
            self.web_browser_get_request,
            self.web_browser_put_request,
            self.web_browser_add_cookie,
            self.web_browser_remove_cookie,
            self.web_browser_get_cookies,
            self.web_browser_update_cookie,
            self.web_browser_get_all_cookies,
            web_input_func
        ]
        
        super().__init__("WebBrowser", system_message, tools, model_client)
        
    async def web_browser_post_request(self, url: str, data: str, cookies: str) -> str:
        """
        Post a request to the given URL with the given data
        
        Args:
            url: The URL to post the request to, example "https://www.google.com".
            data: The data to post to the given URL, example "{\"key\": \"value\"}".
            cookies: The cookies to include in the request, example "{\"JSESSIONID\": \"1234567890\"}".
            
        Returns:
            The result of the operation
        """
        logger.info(f"Calling WebBrowserAPI post_request with url={url}, data={data}, cookies={cookies}")
        result = self.web_browser_api.post_request(url=url, data=data, cookies=cookies)
        return result
        
    async def web_browser_get_request(self, url: str, cookies: str) -> str:
        """
        Get a request from the given URL
        
        Args:
            url: The URL to get the request from, example "https://www.google.com".
            cookies: The cookies to include in the request, example "{\"JSESSIONID\": \"1234567890\"}".
            
        Returns:
            The result of the operation
        """
        logger.info(f"Calling WebBrowserAPI get_request with url={url}, cookies={cookies}")
        result = self.web_browser_api.get_request(url=url, cookies=cookies)
        return result
        
    async def web_browser_put_request(self, url: str, data: str, cookies: str) -> str:
        """
        Put a request to the given URL with the given data
        
        Args:
            url: The URL to put the request to, example "https://www.google.com".
            data: The data to put to the given URL, example "{\"key\": \"value\"}".
            cookies: The cookies to include in the request, example "{\"JSESSIONID\": \"1234567890\"}".
            
        Returns:
            The result of the operation
        """
        logger.info(f"Calling WebBrowserAPI put_request with url={url}, data={data}, cookies={cookies}")
        result = self.web_browser_api.put_request(url=url, data=data, cookies=cookies)
        return result
        
    async def web_browser_add_cookie(self, cookie_name: str, cookie_value: str, cookie_domain: str, cookie_path: str, cookie_expiry: str) -> str:
        """
        Add a cookie to the given URL
        
        Args:
            cookie_name: The name of the cookie to add, example "JSESSIONID".
            cookie_value: The value of the cookie to add, example "1234567890".
            cookie_domain: The domain of the cookie to add, example "google.com".
            cookie_path: The path of the cookie to add, example "/".
            cookie_expiry: The expiry date of the cookie to add, example "01/26".
            
        Returns:
            The result of the operation
        """
        logger.info(f"Calling WebBrowserAPI add_cookie with cookie_name={cookie_name}, cookie_value={cookie_value}, cookie_domain={cookie_domain}, cookie_path={cookie_path}, cookie_expiry={cookie_expiry}")
        result = self.web_browser_api.add_cookie(cookie_name=cookie_name, cookie_value=cookie_value, cookie_domain=cookie_domain, cookie_path=cookie_path, cookie_expiry=cookie_expiry)
        return result 

    async def web_browser_remove_cookie(self, cookie_name: str) -> str:
        """
        Remove a cookie from the given URL
        
        Args:
            cookie_name: The name of the cookie to remove, example "JSESSIONID".
            
        Returns:
            The result of the operation
        """
        logger.info(f"Calling WebBrowserAPI remove_cookie with cookie_name={cookie_name}")
        result = self.web_browser_api.remove_cookie(cookie_name=cookie_name)
        return result

    async def web_browser_get_cookies(self, url: str) -> str:
        """
        Get all the cookies from the given URL
        """
        logger.info(f"Calling WebBrowserAPI get_cookies with url={url}")
        result = self.web_browser_api.get_cookies(url=url)
        return result

    async def web_browser_update_cookie(self, cookie_name: str, cookie_value: str, cookie_domain: str, cookie_path: str, cookie_expiry: str) -> str:
        """
        Update a cookie from the given URL
        
        Args:
            cookie_name: The name of the cookie to update, example "JSESSIONID".
            cookie_value: The value of the cookie to update, example "1234567890".
            cookie_domain: The domain of the cookie to update, example "google.com".
            cookie_path: The path of the cookie to update, example "/".
            cookie_expiry: The expiry date of the cookie to update, example "01/26".
            
        Returns:
            The result of the operation
        """
        logger.info(f"Calling WebBrowserAPI update_cookie with cookie_name={cookie_name}, cookie_value={cookie_value}, cookie_domain={cookie_domain}, cookie_path={cookie_path}, cookie_expiry={cookie_expiry}")
        result = self.web_browser_api.update_cookie(cookie_name=cookie_name, cookie_value=cookie_value, cookie_domain=cookie_domain, cookie_path=cookie_path, cookie_expiry=cookie_expiry)
        return result

    async def web_browser_get_all_cookies(self) -> str:
        """
        Get all the cookies
        """
        logger.info("Calling WebBrowserAPI get_all_cookies")
        result = self.web_browser_api.get_all_cookies()
        return result
    
