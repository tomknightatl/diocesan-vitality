import { useState, useEffect } from 'react';
import { Container, Table, Spinner, Alert, Navbar } from 'react-bootstrap';
import './App.css';

function App() {
  const [dioceses, setDioceses] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    // Use relative URL - Vite proxy will forward to localhost:8000 in development
    fetch('/api/dioceses')
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
                <th>Name</th>
                <th>Address</th>
                <th>Website</th>
              </tr>
            </thead>
            <tbody>
              {dioceses.map((diocese, index) => (
                <tr key={diocese.id || index}>
                  <td>{diocese.id}</td>
                  <td>{diocese.Name}</td>
                  <td>{diocese.Address}</td>
                  <td>{diocese.Website}</td>
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