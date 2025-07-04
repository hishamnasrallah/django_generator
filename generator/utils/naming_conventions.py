"""
Naming Conventions
Handles various naming convention transformations
"""
import re
from typing import List, Optional
import inflection


class NamingConventions:
    """
    Handles naming convention transformations for code generation.

    Supports:
    - snake_case (Python variables, functions)
    - PascalCase (Python classes, Django models)
    - camelCase (JavaScript, JSON)
    - kebab-case (URLs, CSS, HTML)
    - CONSTANT_CASE (Constants)
    - Title Case (Human readable)
    """

    def __init__(self):
        # Common abbreviations that should be preserved
        self.abbreviations = {
            'api', 'url', 'id', 'uuid', 'ip', 'http', 'https', 'ftp',
            'css', 'html', 'js', 'json', 'xml', 'csv', 'pdf',
            'db', 'sql', 'orm', 'crud', 'rest', 'rpc', 'grpc',
            'ui', 'ux', 'seo', 'cdn', 'dns', 'ssl', 'tls',
            'aws', 'gcp', 'azure', 'oauth', 'jwt', 'saml',
            'ci', 'cd', 'vm', 'os', 'io', 'cpu', 'gpu',
        }

        # Compound words that should be treated as single units
        self.compound_words = {
            'username', 'password', 'email', 'timestamp', 'datetime',
            'filename', 'filepath', 'endpoint', 'webhook', 'callback',
            'dropdown', 'checkbox', 'textarea', 'upload', 'download',
        }

    def to_snake_case(self, text: str) -> str:
        """
        Convert to snake_case.

        Examples:
            'UserProfile' -> 'user_profile'
            'getUserByID' -> 'get_user_by_id'
            'kebab-case-example' -> 'kebab_case_example'
        """
        # Handle already snake_case
        if self._is_snake_case(text):
            return text.lower()

        # Convert from other formats
        text = self._prepare_text(text)

        # Handle camelCase and PascalCase
        text = re.sub('([a-z0-9])([A-Z])', r'\1_\2', text)

        # Handle sequences of capitals
        text = re.sub('([A-Z]+)([A-Z][a-z])', r'\1_\2', text)

        # Replace non-alphanumeric with underscore
        text = re.sub(r'[^\w]+', '_', text)

        # Remove leading/trailing underscores and convert to lowercase
        text = text.strip('_').lower()

        # Handle multiple underscores
        text = re.sub(r'_+', '_', text)

        return text

    def to_pascal_case(self, text: str) -> str:
        """
        Convert to PascalCase.

        Examples:
            'user_profile' -> 'UserProfile'
            'get-user-by-id' -> 'GetUserById'
            'API_TOKEN' -> 'ApiToken'
        """
        # Handle already PascalCase
        if self._is_pascal_case(text):
            return text

        # Convert to snake_case first
        snake = self.to_snake_case(text)

        # Split and capitalize
        parts = snake.split('_')

        # Handle abbreviations
        capitalized_parts = []
        for part in parts:
            if part.lower() in self.abbreviations:
                capitalized_parts.append(part.upper() if len(part) <= 3 else part.capitalize())
            else:
                capitalized_parts.append(part.capitalize())

        return ''.join(capitalized_parts)

    def to_camel_case(self, text: str) -> str:
        """
        Convert to camelCase.

        Examples:
            'user_profile' -> 'userProfile'
            'get-user-by-id' -> 'getUserById'
            'APIToken' -> 'apiToken'
        """
        pascal = self.to_pascal_case(text)
        if not pascal:
            return ''

        # Handle abbreviations at the start
        if len(pascal) > 1 and pascal[:2].isupper():
            # Find where the uppercase sequence ends
            i = 0
            while i < len(pascal) and pascal[i].isupper():
                i += 1

            if i > 1:
                # Keep all but last uppercase letter lowercased
                return pascal[:i-1].lower() + pascal[i-1:]

        return pascal[0].lower() + pascal[1:]

    def to_kebab_case(self, text: str) -> str:
        """
        Convert to kebab-case.

        Examples:
            'UserProfile' -> 'user-profile'
            'get_user_by_id' -> 'get-user-by-id'
            'API_TOKEN' -> 'api-token'
        """
        snake = self.to_snake_case(text)
        return snake.replace('_', '-')

    def to_constant_case(self, text: str) -> str:
        """
        Convert to CONSTANT_CASE.

        Examples:
            'UserProfile' -> 'USER_PROFILE'
            'get-user-by-id' -> 'GET_USER_BY_ID'
            'apiToken' -> 'API_TOKEN'
        """
        snake = self.to_snake_case(text)
        return snake.upper()

    def to_title_case(self, text: str) -> str:
        """
        Convert to Title Case (human readable).

        Examples:
            'user_profile' -> 'User Profile'
            'getUserById' -> 'Get User By Id'
            'API_TOKEN' -> 'API Token'
        """
        # Convert to snake case first
        snake = self.to_snake_case(text)

        # Split and capitalize
        words = snake.split('_')

        # Handle special words
        titled_words = []
        for word in words:
            if word.lower() in self.abbreviations and len(word) <= 3:
                titled_words.append(word.upper())
            else:
                titled_words.append(word.capitalize())

        return ' '.join(titled_words)

    def to_human_readable(self, text: str) -> str:
        """
        Convert to human readable format.

        Examples:
            'user_profile' -> 'user profile'
            'isActive' -> 'is active'
            'CONSTANT_VALUE' -> 'constant value'
        """
        snake = self.to_snake_case(text)
        return snake.replace('_', ' ')

    def to_plural(self, text: str) -> str:
        """
        Convert to plural form while preserving case.

        Examples:
            'User' -> 'Users'
            'user_profile' -> 'user_profiles'
            'Company' -> 'Companies'
        """
        # Detect original case
        if self._is_pascal_case(text):
            singular = inflection.singularize(text)
            plural = inflection.pluralize(singular)
            return plural
        elif self._is_camel_case(text):
            # Convert to snake, pluralize, then back to camel
            snake = self.to_snake_case(text)
            plural_snake = inflection.pluralize(snake)
            return self.to_camel_case(plural_snake)
        elif self._is_kebab_case(text):
            parts = text.split('-')
            parts[-1] = inflection.pluralize(parts[-1])
            return '-'.join(parts)
        else:
            # Assume snake_case or constant
            parts = text.split('_')
            parts[-1] = inflection.pluralize(parts[-1])
            return '_'.join(parts)

    def to_singular(self, text: str) -> str:
        """
        Convert to singular form while preserving case.

        Examples:
            'Users' -> 'User'
            'user_profiles' -> 'user_profile'
            'Companies' -> 'Company'
        """
        # Detect original case
        if self._is_pascal_case(text):
            return inflection.singularize(text)
        elif self._is_camel_case(text):
            # Convert to snake, singularize, then back to camel
            snake = self.to_snake_case(text)
            singular_snake = inflection.singularize(snake)
            return self.to_camel_case(singular_snake)
        elif self._is_kebab_case(text):
            parts = text.split('-')
            parts[-1] = inflection.singularize(parts[-1])
            return '-'.join(parts)
        else:
            # Assume snake_case or constant
            parts = text.split('_')
            parts[-1] = inflection.singularize(parts[-1])
            return '_'.join(parts)

    def to_django_model_name(self, text: str) -> str:
        """
        Convert to Django model name (PascalCase, singular).

        Examples:
            'user_profiles' -> 'UserProfile'
            'blog-posts' -> 'BlogPost'
            'categories' -> 'Category'
        """
        singular = self.to_singular(text)
        return self.to_pascal_case(singular)

    def to_django_field_name(self, text: str) -> str:
        """
        Convert to Django field name (snake_case).

        Examples:
            'FirstName' -> 'first_name'
            'isActive' -> 'is_active'
            'user-email' -> 'user_email'
        """
        return self.to_snake_case(text)

    def to_django_related_name(self, from_model: str, to_model: str, field_name: str) -> str:
        """
        Generate Django related_name for relationships.

        Examples:
            ('User', 'Post', 'author') -> 'authored_posts'
            ('Category', 'Post', 'category') -> 'posts'
            ('User', 'Profile', 'user') -> 'profile'
        """
        from_model_snake = self.to_snake_case(from_model)
        to_model_snake = self.to_snake_case(to_model)
        field_snake = self.to_snake_case(field_name)

        # If field name is just the model name, use simple plural
        if field_snake == from_model_snake.lower():
            return inflection.pluralize(to_model_snake)

        # Otherwise, create descriptive related name
        if field_snake.endswith('_' + from_model_snake):
            prefix = field_snake[:-len('_' + from_model_snake)]
            return f"{prefix}_{inflection.pluralize(to_model_snake)}"
        else:
            return f"{field_snake}_{inflection.pluralize(to_model_snake)}"

    def to_url_pattern(self, text: str) -> str:
        """
        Convert to URL pattern (kebab-case, plural for collections).

        Examples:
            'UserProfile' -> 'user-profiles'
            'blog_post' -> 'blog-posts'
            'APIKey' -> 'api-keys'
        """
        kebab = self.to_kebab_case(text)
        return inflection.pluralize(kebab)

    def to_javascript_variable(self, text: str) -> str:
        """
        Convert to JavaScript variable name (camelCase).

        Examples:
            'user_profile' -> 'userProfile'
            'API_KEY' -> 'apiKey'
            'get-data' -> 'getData'
        """
        return self.to_camel_case(text)

    def to_css_class(self, text: str) -> str:
        """
        Convert to CSS class name (kebab-case).

        Examples:
            'UserProfile' -> 'user-profile'
            'primary_button' -> 'primary-button'
            'isActive' -> 'is-active'
        """
        return self.to_kebab_case(text)

    def to_file_name(self, text: str, extension: Optional[str] = None) -> str:
        """
        Convert to file name (snake_case).

        Examples:
            'UserProfile' -> 'user_profile.py'
            'APITests' -> 'api_tests.py'
            'MainComponent' -> 'main_component.js'
        """
        snake = self.to_snake_case(text)
        if extension:
            return f"{snake}.{extension.lstrip('.')}"
        return snake

    # Helper methods

    def _prepare_text(self, text: str) -> str:
        """Prepare text for conversion by normalizing separators."""
        # Replace common separators with spaces
        text = re.sub(r'[-.\s/\\]+', ' ', text)
        return text.strip()

    def _is_snake_case(self, text: str) -> bool:
        """Check if text is in snake_case."""
        return bool(re.match(r'^[a-z]+(_[a-z]+)*$', text))

    def _is_pascal_case(self, text: str) -> bool:
        """Check if text is in PascalCase."""
        return bool(re.match(r'^[A-Z][a-zA-Z0-9]*$', text))

    def _is_camel_case(self, text: str) -> bool:
        """Check if text is in camelCase."""
        return bool(re.match(r'^[a-z][a-zA-Z0-9]*$', text))

    def _is_kebab_case(self, text: str) -> bool:
        """Check if text is in kebab-case."""
        return bool(re.match(r'^[a-z]+(-[a-z]+)*$', text))

    def _is_constant_case(self, text: str) -> bool:
        """Check if text is in CONSTANT_CASE."""
        return bool(re.match(r'^[A-Z]+(_[A-Z]+)*$', text))


class DjangoNamingHelper:
    """Helper class specifically for Django naming conventions."""

    def __init__(self):
        self.conventions = NamingConventions()

    def get_verbose_name(self, field_name: str) -> str:
        """
        Get verbose name for a field.

        Examples:
            'first_name' -> 'first name'
            'email_address' -> 'email address'
            'isActive' -> 'is active'
        """
        return self.conventions.to_human_readable(field_name)

    def get_db_table_name(self, app_label: str, model_name: str) -> str:
        """
        Get database table name.

        Examples:
            ('blog', 'Post') -> 'blog_post'
            ('auth', 'UserProfile') -> 'auth_userprofile'
        """
        app_snake = self.conventions.to_snake_case(app_label)
        model_snake = self.conventions.to_snake_case(model_name)
        return f"{app_snake}_{model_snake}"

    def get_migration_name(self, description: str, number: int = 1) -> str:
        """
        Get migration file name.

        Examples:
            ('add user profile', 1) -> '0001_add_user_profile.py'
            ('create initial', 1) -> '0001_create_initial.py'
        """
        clean_desc = self.conventions.to_snake_case(description)
        # Remove common words
        clean_desc = re.sub(r'\b(the|a|an|and|or|but|in|on|at|to|for)\b', '', clean_desc)
        clean_desc = re.sub(r'_+', '_', clean_desc).strip('_')

        return f"{number:04d}_{clean_desc[:50]}.py"

    def get_app_config_name(self, app_name: str) -> str:
        """
        Get Django AppConfig class name.

        Examples:
            'blog' -> 'BlogConfig'
            'user_profile' -> 'UserProfileConfig'
        """
        return self.conventions.to_pascal_case(app_name) + 'Config'

    def get_admin_class_name(self, model_name: str) -> str:
        """
        Get Django admin class name.

        Examples:
            'Post' -> 'PostAdmin'
            'UserProfile' -> 'UserProfileAdmin'
        """
        return self.conventions.to_pascal_case(model_name) + 'Admin'

    def get_form_class_name(self, model_name: str, form_type: str = '') -> str:
        """
        Get Django form class name.

        Examples:
            ('Post', '') -> 'PostForm'
            ('User', 'Registration') -> 'UserRegistrationForm'
            ('Profile', 'Update') -> 'ProfileUpdateForm'
        """
        base = self.conventions.to_pascal_case(model_name)
        if form_type:
            form_type = self.conventions.to_pascal_case(form_type)
            return f"{base}{form_type}Form"
        return f"{base}Form"

    def get_serializer_class_name(self, model_name: str, serializer_type: str = '') -> str:
        """
        Get DRF serializer class name.

        Examples:
            ('Post', '') -> 'PostSerializer'
            ('User', 'List') -> 'UserListSerializer'
            ('Profile', 'Detail') -> 'ProfileDetailSerializer'
        """
        base = self.conventions.to_pascal_case(model_name)
        if serializer_type:
            serializer_type = self.conventions.to_pascal_case(serializer_type)
            return f"{base}{serializer_type}Serializer"
        return f"{base}Serializer"

    def get_viewset_class_name(self, model_name: str) -> str:
        """
        Get DRF viewset class name.

        Examples:
            'Post' -> 'PostViewSet'
            'UserProfile' -> 'UserProfileViewSet'
        """
        return self.conventions.to_pascal_case(model_name) + 'ViewSet'

    def get_test_class_name(self, model_name: str, test_type: str = 'Model') -> str:
        """
        Get test class name.

        Examples:
            ('Post', 'Model') -> 'PostModelTest'
            ('User', 'API') -> 'UserAPITest'
            ('Profile', 'View') -> 'ProfileViewTest'
        """
        base = self.conventions.to_pascal_case(model_name)
        test_type = self.conventions.to_pascal_case(test_type)
        return f"{base}{test_type}Test"