import utility_classes
import error_classes
import logging
from utility_classes import uvm_void
from s05_base_classes import uvm_object
from s13_predefined_component_classes import uvm_component
# from predefined_component_classes import uvm_object
from s13_predefined_component_classes import uvm_component


# Implementing section 8 in the IEEE Specification
# The IEEE spec assumes that UVM is being written in SystemVerilog,
# a language that does not allow you to control how classes get defined.
# Python has more control in this area. With Python we can set things up
# so that any class that extends uvm_void automatically gets registered
# into the factory.

# Therefore there is no need for 8.2.2 the type_id, that is a SystemVerilog artifact as is 8.2.3
# There is also no need for 8.2.4, the uvm_object_registry.  The FactoryMeta class causes
# all classes from uvm_void down to automatically register themselves with the factory
# by copying themselves into a dict.

# However there is a need to provide the methods in 8.



class uvm_factory(metaclass=utility_classes.Singleton):
    """
    8.3.1.1
    The uvm_factory is a singleton that delivers all factory functions.
    """

    # 8.3.1.2.1 get
    # There is no get() method in Python singletons.  Instead you instantiate
    # the singleton as normal and you automatically get the singleton.

    # 8.3.1.3 register
    # Not implemented
    # There is no register in pyuvm.  Instead the factory builds its class
    # database through introspection.

    def __init__(self):
        self.fd = utility_classes.FactoryData()
        self.logger = logging.getLogger("Factory")

    def set_override(self, original, override, path = None):
        if original not in self.fd.overrides:
            self.fd.overrides[original] = utility_classes.Override()
        self.fd.overrides[original].add(override, path)




    def set_inst_override_by_type(self, original_type, override_type, full_inst_path):
        """
        8.3.1.3 Implementation
        :param original_type: The original type being overridden
        :param override_type: The overriding type
        :param full_inst_path: The inst where this happens.

        The intention here is to only override when a type of original_type is at the
        full_inst_path provided. If someone stores a different class at full_inst_path
        then the override will not happen.

        We capture this by storing the original and override types as a tuple at the full
        inst path.  Later we'll retrieve the tuple and check the type of the object at
        the full_inst_path.

        instance_overrides is an OrderedDict, so we will check the paths in the order they
        are registered later.
        """
        assert issubclass(original_type, utility_classes.uvm_void), "You tried to override a non-uvm_void class"
        assert issubclass(override_type, utility_classes.uvm_void), "You tried to use a non-uvm_void class as an override"
        self.set_override(original_type, override_type, full_inst_path)



    def set_inst_override_by_name(self, original_type_name, override_type_name, full_inst_path):
        """
        8.3.1.4.1
        Here we use the names of classes instead of the classes.  The original_name
        doesn't need to be the name of a class, it can be an arbitrary string. The
        override_name must be the name of a class.

        Later we will retrieve this by searching through the keys for a match to
        a path and then checking that the name given in the search matches the
        original_name
        :param original:
        :param override:
        :return:
        """
        assert isinstance(full_inst_path, str), "The inst_path must be a string"
        assert isinstance(original_type_name, str), "Original_name must be a string"
        assert isinstance(override_type_name, str), "Override_name must be a string"
        try:
            override_type = self.fd.classes[override_type_name]
        except KeyError:
            raise error_classes.UVMFactoryError(f"{override_name}" + " has not been defined.")

        # Set type override by name can use an arbitrary string as a key instead of a type
        # Fortunately Python dicts don't care about the type of the key.
        try:
            original_type = self.fd.classes[original_type_name]
        except KeyError:
            original_type = original_type_name

        self.set_override(original_type, override_type, full_inst_path)


    def set_type_override_by_type(self, original_type, override_type, replace=True):
        """
        8.3.1.4.2
        :param original_type: The original type to be overridden
        :param override_type: The new type that will override it
        :param replace: If the override exists, only replace it if this is True
        """
        assert issubclass(original_type, utility_classes.uvm_void), "You tried to override a non-uvm_void class"
        assert issubclass(override_type, utility_classes.uvm_void), "You tried to use a non-uvm_void class as an override"
        if (original_type not in self.fd.overrides) or replace:
            self.set_override(original_type, override_type)

    def set_type_override_by_name(self, original_type_name, override_type_name, replace=True):
        """
        8.3.1.4.2
        :param original_type_name: The name of the type to be overridden or an arbitrary string.
        :param override_type_name: The name of the overriding type. It must have been declared.
        :param replace: If the override already exists only replace if this is True
        :return:
        """
        assert isinstance(original_type_name, str), "Original_name must be a string"
        assert isinstance(override_type_name, str), "Override_name must be a string"
        try:
            override_type = self.fd.classes[override_type_name]
        except KeyError:
            raise error_classes.UVMFactoryError(f"{override_type_name}" + " has not been defined.")

        # Set type override by name can use an arbitrary string as a key instead of a type
        # Fortunately Python dicts don't care about the type of the key.
        try:
            original_type = self.fd.classes[original_type_name]
        except KeyError:
            original_type = original_type_name

        if (original_type not in self.fd.overrides) or replace:
            self.set_override(original_type, override_type)

    def __find_override(self, requested_type, parent_inst_path=None, name=None):
        """
        An internal function that finds overrides
        :param requested_type: The type that could be overridden
        :param parent_inst_path: The parent inst path for an override
        :param name: The name of the object, concatenated with parent inst path for override
        :return: either the requested_type or its override
        """
        if not isinstance(requested_type, str):
            assert (issubclass(requested_type, uvm_void)), \
                f"You can only create uvm_void descendents not {requested_type}"

        if name is not None:
            assert(isinstance(name, str)), "name must be a string"
        else:
            name = ""

        if parent_inst_path is not None:
            assert isinstance(parent_inst_path, str), "parent_inst_path must be a string"
            inst_name = f"{parent_inst_path}.{name}"
        else:
            inst_name = None

        new_cls =  self.fd.find_override(requested_type, inst_name)
        if isinstance(new_cls, str):
            self.logger.error(f'"{new_cls}" is not declared and is not an override string')
            return None
        else:
            return new_cls

    def create_object_by_type(self, requested_type, parent_inst_path=None, name=None):
        """
        8.3.1.5 Creation
        :param requeested_type: The type that we request but that can be overridden
        :param parent_inst_path: The get_full_name path of the parrent
        :param name: The name of the instance requested_type("name")
        :return: Type that is child of uvm_object.
        Python does not create zero-length strings as defaults. It puts the None object there. That's
        what we're going to do.
        """
        new_type = self.__find_override(requested_type, parent_inst_path, name)
        if new_type is None:
            return None
        if not issubclass(new_type, uvm_object):
            self.logger.error(f"{new_type} is not a subclass of uvm_object")
            return None
        else:
            return new_type(name)


    def create_object_by_name(self, requested_type_name, parent_inst_path=None, name=None):
        """
        8.3.1.5 createing an object by name.
        :param requested_type_name: the type that could be overridden
        :param parent_inst_path: A path if we are checking for inst overrides
        :param name: The name of the new object.
        :return: A uvm_object with the name given
        """
        try:
            requested_type = utility_classes.FactoryData().classes[requested_type_name]
        except KeyError:
            requested_type = requested_type_name

        new_obj =  self.create_object_by_type(requested_type, parent_inst_path, name)
        return new_obj (name)

    def create_component_by_type(self, requested_type, parent_inst_path=None, name=None, parent=None):
        """
        8.3.1.5 creating a component
        :param requested_type: Type type to be overriden
        :param parent_inst_path: The inst path if ew are looking for inst overrides
        :param name: Concatenated with parent_inst_path if it exists for inst overrides
        :param parent: The parent component
        :return: a uvm_component with the name an parent given.
        """

        if name is None:
            raise error_classes.UVMFactoryError("Parameter name must be specified in function call.")

        new_type = self.__find_override(requested_type, parent_inst_path, name)

        if new_type is None:
            return None

        if not issubclass(new_type, uvm_component):
            self.logger.error(f"{new_type} is not a subclass of uvm_component")
            return None
        else:
            new_comp = new_type(name, parent)
            return new_comp

    def create_component_by_name(self, requested_type_name, parent_inst_path=None, name=None, parent=None):
        """
        8.3.1.5 creating an component by name.
        :param requested_type_name: the type that could be overridden
        :param parent_inst_path: A path if we are checking for inst overrides
        :param name: The name of the new object.
        :return: A uvm_object with the name given
        """
        if name is None:
            raise error_classes.UVMFactoryError("Parameter name must be specified in create_component_by_name.")

        try:
            requested_type = utility_classes.FactoryData().classes[requested_type_name]
        except KeyError:
            requested_type = requested_type_name

        new_obj =  self.create_component_by_type(requested_type, parent_inst_path, name, parent)
        return new_obj
