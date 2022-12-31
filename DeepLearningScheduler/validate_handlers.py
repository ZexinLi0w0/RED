# required attributes in config file
HandlerAttributes = ["id", "name", "description"]

def validate_handlers(handlers):
    """
    Function to validate the handlers in the handler list.
    """
    # def check_dependencies(handler_id, visited):
    #     """
    #     Recursive function to check if the handler dependencies have a circular reference.
    #     """
    #     handler = next((t for t in handlers if t["id"] == handler_id), None)
    #     if handler is None:
    #         return
    #     if handler["id"] in visited:
    #         raise ValueError(f"Invalid handler #{handler['id']}: circular dependencies found")
    #     visited.add(handler["id"])
    #     for dependency in handler["dependencies"]:
    #         check_dependencies(dependency, visited)

    unique_handler_name = set()
    unique_handler_id = set()
    # Validate the handler attributes
    for i, handler in enumerate(handlers):
        # Check if the handler has all required attributes
        missing_attrs = []
        for attr in HandlerAttributes:
            if attr not in handler:
                missing_attrs.append(attr)
        if missing_attrs:
            raise ValueError(f"Invalid handler #{i+1}: missing required attribute(s): {', '.join(missing_attrs)}")
        
        # check if the handler_name and handler_id is unique
        if(handler["name"] in unique_handler_name):
            raise ValueError(f"Handler name must be unique in handler id[{handler['id']}]")
        if(handler["id"] in unique_handler_id):
            raise ValueError(f"Handler id must be unique in handler id[{handler['id']}]")
        unique_handler_name.add(handler["name"])
        unique_handler_id.add(handler["id"])


if __name__ == "__main__":
    # add test cases
    pass