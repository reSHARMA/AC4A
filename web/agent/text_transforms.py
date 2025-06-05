import re
import logging
from typing import Dict, Callable, Any, List

logger = logging.getLogger(__name__)

class TextTransformer:
    """
    A class to handle various text transformations.
    Each transformation is implemented as a method and registered in the transforms dictionary.
    
    Example usage:
    ```python
    from text_transforms import text_transformer
    
    # Basic usage
    result = text_transformer.transform("7th July 2025", "remove_ordinal")  # Returns "7 July 2025"
    
    # Using the process_text_value function
    from text_transforms import process_text_value
    result = process_text_value("7th July 2025", "remove_ordinal")  # Returns "7 July 2025"
    
    # Registering a custom transform
    def my_transform(text: str) -> str:
        return text.replace("old", "new")
    text_transformer.register_transform("replace_old", my_transform)
    ```
    """
    
    def __init__(self):
        # Dictionary to store all available transformations
        self.transforms: Dict[str, Callable[[str], str]] = {
            'remove_ordinal': self.remove_ordinal,
            'to_number': self.to_number,
            'month_to_number': self.month_to_number,
            'number_to_month': self.number_to_month,
            'uppercase': self.uppercase,
            'lowercase': self.lowercase,
            'capitalize': self.capitalize,
            'remove_punctuation': self.remove_punctuation,
            'replace_punctuation': self.replace_punctuation,
            'split_space': self.split_space,
            'split_slash': self.split_slash
        }
        
        # Dictionary mapping month names to numbers
        self.months = {
            '1': 'January',
            '2': 'February',
            '3': 'March',
            '4': 'April',
            '5': 'May',
            '6': 'June',
            '7': 'July',
            '8': 'August',
            '9': 'September',
            '10': 'October',
            '11': 'November',
            '12': 'December'
        }
    
    def transform(self, text: str, transform_name: str) -> str:
        """
        Apply a transformation to the text.
        
        Args:
            text (str): Text to transform
            transform_name (str): Name of the transformation to apply
            
        Returns:
            str: Transformed text
            
        Example:
            ```python
            # Remove ordinal from date
            result = text_transformer.transform("7th July 2025", "remove_ordinal")  # Returns "7 July 2025"
            
            # Convert to uppercase
            result = text_transformer.transform("hello", "uppercase")  # Returns "HELLO"
            ```
        """
        if not transform_name or not text:
            return text
            
        try:
            transform_func = self.transforms.get(transform_name)
            if transform_func:
                return transform_func(text)
            logger.warning(f"Unknown transformation: {transform_name}")
            return text
        except Exception as e:
            logger.error(f"Error applying transformation {transform_name}: {str(e)}")
            return text
    
    def remove_ordinal(self, text: str) -> str:
        """
        Remove ordinal indicators (st, nd, rd, th) from numbers.
        
        Example:
            ```python
            result = text_transformer.remove_ordinal("7th July 2025")  # Returns "7 July 2025"
            result = text_transformer.remove_ordinal("1st January")    # Returns "1 January"
            result = text_transformer.remove_ordinal("2nd February")   # Returns "2 February"
            result = text_transformer.remove_ordinal("3rd March")      # Returns "3 March"
            ```
        """
        return re.sub(r'(\d+)(?:st|nd|rd|th)', r'\1', text)
    
    def to_number(self, text: str) -> str:
        """
        Extract only digits from text.
        
        Example:
            ```python
            result = text_transformer.to_number("7th July 2025")  # Returns "72025"
            result = text_transformer.to_number("Room 101")       # Returns "101"
            result = text_transformer.to_number("Price: $99.99")  # Returns "9999"
            ```
        """
        return re.sub(r'[^\d]', '', text)
    
    def month_to_number(self, text: str) -> str:
        """
        Convert month name to number (1-12).
        
        Example:
            ```python
            result = text_transformer.month_to_number("July")     # Returns "7"
            result = text_transformer.month_to_number("January")  # Returns "1"
            result = text_transformer.month_to_number("December") # Returns "12"
            ```
        """
        text_lower = text.lower()
        # Create reverse mapping for month names to numbers
        month_to_num = {v.lower(): k for k, v in self.months.items()}
        for month, num in month_to_num.items():
            if month in text_lower:
                return num
        return text
    
    def number_to_month(self, text: str) -> str:
        """
        Convert number (1-12) to month name.

        Example:
            ```python
            result = text_transformer.number_to_month("7")  # Returns "July"
            result = text_transformer.number_to_month("1")  # Returns "January"
            result = text_transformer.number_to_month("12") # Returns "December"
            ```
        """
        return self.months[text]
    
    def uppercase(self, text: str) -> str:
        """
        Convert text to uppercase.
        
        Example:
            ```python
            result = text_transformer.uppercase("hello")  # Returns "HELLO"
            result = text_transformer.uppercase("Hi")     # Returns "HI"
            ```
        """
        return text.upper()
    
    def lowercase(self, text: str) -> str:
        """
        Convert text to lowercase.
        
        Example:
            ```python
            result = text_transformer.lowercase("HELLO")  # Returns "hello"
            result = text_transformer.lowercase("Hi")     # Returns "hi"
            ```
        """
        return text.lower()
    
    def capitalize(self, text: str) -> str:
        """
        Capitalize first letter of text.
        
        Example:
            ```python
            result = text_transformer.capitalize("hello")  # Returns "Hello"
            result = text_transformer.capitalize("hi")     # Returns "Hi"
            ```
        """
        return text.capitalize()
    
    def remove_punctuation(self, text: str) -> str:
        """
        Remove punctuation from text.

        Example:
            ```python
            result = text_transformer.remove_punctuation("Hello, world!")  # Returns "Hello world"
            result = text_transformer.remove_punctuation("Hello, world!")  # Returns "Hello world"
            ```
        """
        return re.sub(r'[^\w\s]', '', text)
    
    def replace_punctuation(self, text: str) -> str:
        """
        Replace punctuation with a space.

        Example:
            ```python
            result = text_transformer.replace_punctuation("Hello, world!")  # Returns "Hello  world"
            result = text_transformer.replace_punctuation("Hello, world!")  # Returns "Hello  world"
            ```
        """
        return re.sub(r'[^\w\s]', ' ', text)
    
    def split_space(self, text: str) -> List[str]:
        """
        Split text by space.
        
        Example:
            ```python
            result = text_transformer.split_space("A B C")  # Returns ["A", "B", "C"]
            ```
        """
        return text.split()
    
    def split_slash(self, text: str) -> List[str]:
        """
        Split text by forward slash.
        
        Example:
            ```python
            result = text_transformer.split_slash("A/B C/D E/F")  # Returns ["A", "B C", "D E", "F"]
            ```
        """
        return text.split('/')
    
    def register_transform(self, name: str, transform_func: Callable[[str], str]) -> None:
        """
        Register a new transformation function.
        
        Args:
            name (str): Name of the transformation
            transform_func (Callable[[str], str]): Function that takes a string and returns transformed string
            
        Example:
            ```python
            def replace_old(text: str) -> str:
                return text.replace("old", "new")
                
            text_transformer.register_transform("replace_old", replace_old)
            result = text_transformer.transform("old value", "replace_old")  # Returns "new value"
            ```
        """
        self.transforms[name] = transform_func

# Create a singleton instance
text_transformer = TextTransformer()

def process_text_value(text: str, transform: str = None) -> str:
    """
    Process text value with various transformations.
    
    Args:
        text (str): Text to process
        transform (str): Transformation to apply
        
    Returns:
        str: Processed text
        
    Example:
        ```python
        # Remove ordinal from date
        result = process_text_value("7th July 2025", "remove_ordinal")  # Returns "7 July 2025"
        
        # Convert month to number
        result = process_text_value("July", "month_to_number")  # Returns "7"
        
        # Chain transformations (using the transformer directly)
        text = "7th July 2025"
        text = text_transformer.transform(text, "remove_ordinal")  # "7 July 2025"
        text = text_transformer.transform(text, "uppercase")       # "7 JULY 2025"
        ```
    """
    return text_transformer.transform(text, transform) 