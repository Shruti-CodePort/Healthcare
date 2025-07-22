# validators.py

class Validator:
    @staticmethod
    def validate_password(password, confirm_password):
        errors = []
        
        if not password or not confirm_password:
            errors.append('Password fields cannot be empty')
            return errors
            
        if password != confirm_password:
            errors.append('Passwords do not match')
            
        if len(password) < 8:
            errors.append('Password must be at least 8 characters long')
            
        if not any(char.isupper() for char in password):
            errors.append('Password must contain at least one uppercase letter')
            
        if not any(char.islower() for char in password):
            errors.append('Password must contain at least one lowercase letter')
            
        if not any(char.isdigit() for char in password):
            errors.append('Password must contain at least one number')
            
        if not any(char in "!@#$%^&*()_+-=[]{}|;:,.<>?" for char in password):
            errors.append('Password must contain at least one special character')
            
        return errors

    @staticmethod
    def validate_email(email):
        errors = []
        
        if not email:
            errors.append('Email cannot be empty')
            return errors
            
        if not email.endswith('@gmail.com'):
            errors.append('Only Gmail addresses are allowed')
            
        return errors

    @staticmethod
    def validate_name(full_name):
        errors = []
        
        if not full_name:
            errors.append('Name field cannot be empty')
            return errors
        
        # Split full name into parts
        name_parts = full_name.split()
        
        if len(name_parts) < 2:
            errors.append('Please provide both first and last name')
            return errors
            
        # Check if name contains only letters and spaces
        if not all(part.isalpha() for part in name_parts):
            errors.append('Name should only contain letters')
            
        # Check minimum length for each part of the name
        if any(len(part) < 2 for part in name_parts):
            errors.append('Each part of your name should be at least 2 characters long')
            
        # Check maximum length
        if len(full_name) > 100:
            errors.append('Name is too long (maximum 100 characters)')
            
        return errors