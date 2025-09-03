import { useState, useEffect } from 'react';
import { Container, Table, Spinner, Alert, Navbar } from 'react-bootstrap';
import './App.css';

function App() {
  const [dioceses, setDioceses] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetch('http://api.diocesevitality.org/api/dioceses')
      .then(response => {
        if (!response.ok) {
          throw new Error('Network response was not ok');
        }
        return response.json();
      })
      .then(data => {
        // Check if the backend returned an error
        if (data.error) {
          throw new Error(data.error);
        }
        setDioceses(data);
        setLoading(false);
      })
      .catch(error => {
        setError(error.message);
        setLoading(false);
      });
  }, []); // The empty dependency array ensures this effect runs only once on mount

  return (
    <>
      <Navbar bg="dark" variant="dark">
        <Container>
          <Navbar.Brand href="#home">USCCB Diocese Vitality Index</Navbar.Brand>
        </Container>
      </Navbar>
      <Container className="mt-4">
        <h2>Dioceses Data</h2>
        <p>Displaying the first 20 records from the database.</p>
        {loading && <Spinner animation="border" />}
        {error && <Alert variant="danger">Error fetching data: {error}</Alert>}
        {!loading && !error && (
          <Table striped bordered hover responsive>
            <thead>
              <tr>
                <th>ID</th>
                <th>Diocese Name</th>
                <th>City</th>
                <th>State</th>
              </tr>
            </thead>
            <tbody>
              {dioceses.map(diocese => (
                <tr key={diocese.id}>
                  <td>{diocese.id}</td>
                  <td>{diocese.diocese_name}</td>
                  <td>{diocese.city}</td>
                  <td>{diocese.state}</td>
                </tr>
              ))}
            </tbody>
          </Table>
        )}
      </Container>
    </>
  );
}

export default App;