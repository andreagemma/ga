#include <pybind11/pybind11.h>

#include <sstream>
#include <string>

namespace py = pybind11;

namespace ga {
namespace ctest {

class NumericBuffer {
 public:
  explicit NumericBuffer(double initial = 0.0) : value_(initial) {}

  double add(double delta) {
    value_ += delta;
    return value_;
  }

  double scale(double factor) {
    value_ *= factor;
    return value_;
  }

  double value() const { return value_; }

  void reset(double value = 0.0) { value_ = value; }

  std::string repr() const {
    std::ostringstream stream;
    stream << "NumericBuffer(value=" << value_ << ")";
    return stream.str();
  }

 private:
  double value_;
};

}  // namespace ctest
}  // namespace ga

PYBIND11_MODULE(_ctest, m) {
  m.doc() =
      "Modulo C++ di esempio che esporta la classe NumericBuffer per Python";

  py::class_<ga::ctest::NumericBuffer>(m, "NumericBuffer",
                                      "Classe C++ che gestisce un accumulatore "
                                      "numerico.")
      .def(py::init<double>(), py::arg("initial") = 0.0,
           "Crea un accumulatore inizializzato al valore specificato.")
      .def("add", &ga::ctest::NumericBuffer::add, py::arg("delta"),
           "Somma il valore fornito e restituisce il valore aggiornato.")
      .def("scale", &ga::ctest::NumericBuffer::scale, py::arg("factor"),
           "Moltiplica il valore corrente per il fattore dato e restituisce il "
           "risultato.")
      .def("reset", &ga::ctest::NumericBuffer::reset, py::arg("value") = 0.0,
           "Reimposta l'accumulatore al valore specificato (default 0.0).")
      .def_property_readonly("value", &ga::ctest::NumericBuffer::value,
                             "Restituisce il valore corrente dell'accumulatore.")
      .def("__repr__", &ga::ctest::NumericBuffer::repr);
}
