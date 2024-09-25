import plang.PythonType;

import java.util.Collections;

import plang.PythonObject;
public class main {

    public static void main(String[] args) {

        PythonType fooType = new PythonType("Foo", null);
        PythonType barType = new PythonType("Bar", fooType);
        System.out.println(Collections.singletonList(barType));
        System.out.println("Hello, world!");
    }
}
