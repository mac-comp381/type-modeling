# -*- coding: utf-8 -*-

from .types import (
    JavaBuiltInTypes,
    JavaTypeError,
    NoSuchJavaMethod,
)

class JavaExpression(object):
    """AST for simple Java expressions.

    Note that this library deals only with compile-time types, and this class therefore does not
    actually *evaluate* expressions.
    """

    def static_type(self):
        """Returns the compile-time type of this expression as a JavaType.

        Subclasses must override this method.
        """
        raise NotImplementedError(type(self).__name__ + " must override static_type()")

    def check_types(self):
        """Examines the structure of this expression for static type errors.

        Raises a JavaTypeError if there is an error. If there is no error, this method has no effect
        and returns nothing.

        Subclasses must override this method.
        """
        raise NotImplementedError(type(self).__name__ + " must override check_types()")
    

class JavaVariable(JavaExpression):
    """An expression that reads the value of a variable, e.g. `x` in the expression `x + 5`.

    In a real Java language implementation, the declared_type would be filled in by a name resolver
    after the initial construction of the AST. In this sample project, however, we simply specify
    the declared_type for every variable reference.
    """
    def __init__(self, name, declared_type):
        self.name = name
        self.declared_type = declared_type

    def static_type(self):
        return self.declared_type
    
    def check_types(self):
        pass  # variables do not have type errors on their own 

class JavaLiteral(JavaExpression):
    """A literal value entered in the code, e.g. `5` in the expression `x + 5`.
    """
    def __init__(self, value, type):
        self.value = value  #: The literal value, as a string
        self.type = type    #: The type of the literal (JavaType)

    def static_type(self):
        return self.type

    def check_types(self):
        pass  # just a literal, no type errors


class JavaNullLiteral(JavaLiteral):
    """The literal value `null` in Java code.
    """
    def __init__(self):
        super().__init__("null", JavaBuiltInTypes.NULL)

    def static_type(self):
        return self.type  


class JavaAssignment(JavaExpression):
    """The assignment of a new value to a variable.

    Attributes:
        lhs (JavaVariable): The variable whose value this assignment updates.
        rhs (JavaExpression): The expression whose value will be assigned to the lhs.
    """
    def __init__(self, lhs, rhs):
        self.lhs = lhs
        self.rhs = rhs

    def static_type(self):
        return self.lhs.static_type()
    

    def check_types(self):
        # first, check types of lhs and rhs expressions
        self.lhs.check_types()
        self.rhs.check_types()

        # get the static types of lhs and rhs
        lhs_type = self.lhs.static_type()
        rhs_type = self.rhs.static_type()

        # check if RHS type is a subtype of LHS type
        if not rhs_type.is_subtype_of(lhs_type):
            # prepare error message
            lhs_type_name = lhs_type.name
            rhs_type_name = rhs_type.name

            # get the variable name from lhs if it's a JavaVariable
            if isinstance(self.lhs, JavaVariable):
                variable_name = self.lhs.name
                error_message = f"Cannot assign {rhs_type_name} to variable {variable_name} of type {lhs_type_name}"
            else:
                # if lhs is not a variable, use a generic message
                error_message = f"Cannot assign {rhs_type_name} to {lhs_type_name}"

            # raise a JavaTypeMismatchError
            raise JavaTypeMismatchError(error_message)

        

class JavaMethodCall(JavaExpression):
    """A Java method invocation.

    For example, in this Java code::

        foo.bar(0, 1)

    - The receiver is `JavaVariable(foo, JavaObjectType(...))`
    - The method_name is `"bar"`
    - The args are `[JavaLiteral("0", JavaBuiltInTypes.INT), ...etc...]`

    Attributes:
        receiver (JavaExpression): The object whose method we are calling
        method_name (String): The name of the method to call
        args (list of Expressions): The arguments to pass to the method
    """
    def __init__(self, receiver, method_name, *args):
        self.receiver = receiver
        self.method_name = method_name
        self.args = args

    def static_type(self):
        # Get the static type of the receiver
        receiver_type = self.receiver.static_type()

        # Ensure the receiver is an object type
        if not receiver_type.is_object_type:
            raise JavaTypeError(
                f"Cannot call method {self.method_name} on primitive type {receiver_type.name}"
            )

        # Find the method in the receiver's type
        try:
            method = receiver_type.method_named(self.method_name)
        except NoSuchJavaMethod as e:
            raise JavaTypeError(str(e))

        # Return the method's return type
        return method.return_type

    def check_types(self):
        # First, check the receiver expression
        self.receiver.check_types()
        receiver_type = self.receiver.static_type()

        # Ensure the receiver is an object type
        if not receiver_type.is_object_type:
            raise NoSuchJavaMethod(f"Type {receiver_type.name} does not have methods")

        # Try to find the method in the receiver's type
        try:
            method = receiver_type.method_named(self.method_name)
        except NoSuchJavaMethod as e:
            # Re-raise the exception to preserve the specific message
            raise NoSuchJavaMethod(str(e))

        # Check the number of arguments
        expected_arg_count = len(method.parameter_types)
        actual_arg_count = len(self.args)

        if expected_arg_count != actual_arg_count:
            raise JavaArgumentCountError(
                f"Wrong number of arguments for {receiver_type.name}.{self.method_name}(): "
                f"expected {expected_arg_count}, got {actual_arg_count}"
            )

        # Check each argument's type
        for arg_expr, param_type in zip(self.args, method.parameter_types):
            arg_expr.check_types()
            arg_type = arg_expr.static_type()

            if not arg_type.is_subtype_of(param_type):
                expected_types = [ptype.name for ptype in method.parameter_types]
                actual_types = [arg.static_type().name for arg in self.args]
                raise JavaTypeMismatchError(
                    f"{receiver_type.name}.{self.method_name}() expects arguments of type "
                    f"({', '.join(expected_types)}), but got "
                    f"({', '.join(actual_types)})"
                )



# Helper method for formatting lists
def _comma_separated_list(items):
    return ", ".join(items)

    
    
class JavaConstructorCall(JavaExpression):
    """
    A Java object instantiation

    For example, in this Java code::

        new Foo(0, 1, 2)

    - The instantiated_type is `JavaObjectType("Foo", ...)`
    - The args are `[JavaLiteral("0", JavaBuiltInTypes.INT), ...etc...]`

    Attributes:
        instantiated_type (JavaType): The type to instantiate
        args (list of Expressions): Constructor arguments
    """
    def __init__(self, instantiated_type, *args):
        self.instantiated_type = instantiated_type
        self.args = args


class JavaTypeMismatchError(JavaTypeError):
    """Indicates that one or more expressions do not evaluate to the correct type.
    """
    pass


class JavaArgumentCountError(JavaTypeError):
    """Indicates that a call to a method or constructor has the wrong number of arguments.
    """
    pass


class JavaIllegalInstantiationError(JavaTypeError):
    """Raised in response to `new Foo()` where `Foo` is not an instantiable type.
    """
    pass


def _names(named_things):
    """Helper for formatting pretty error messages
    """
    return "(" + ", ".join([e.name for e in named_things]) + ")"
