import os
import json

def extract_course_test(base_path):
    course_tests = []
    
    # Iterate through each folder in the base directory
    for course_code in os.listdir(base_path):
        course_path = os.path.join(base_path, course_code)
        
        # Ensure it's a directory
        if os.path.isdir(course_path):
            
            # Iterate through files in the folder
            for filename in os.listdir(course_path):
                if filename.endswith(".json"):
                    
                    # Extract the test name from the filename
                    parts = filename.split("_", 1)  # Split from first underscore
                    if len(parts) == 2:
                        test_name = parts[1]  # Test name before the underscore
                        
                        # Store in a structured format
                        course_tests.append({
                            "course_code": course_code,
                            "test": test_name
                        })
    
    return course_tests

# Define base directory
base_directory = "/Users/akarshhegde/Downloads/B_Tech_Complete_Data"

# Get course-test mapping
data = extract_course_test(base_directory)

# Save the result to a JSON file
output_file = "course_test_mapping.json"
with open(output_file, "w") as f:
    json.dump(data, f, indent=4)

print(f"Course-test mapping saved to {output_file}")