import { useState, useEffect } from 'react';
import { Container, Table, Spinner, Alert, Navbar } from 'react-bootstrap';
import './App.css';

function App() {
  const [dioceses, setDioceses] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const [summary, setSummary] = useState(null);
  const [summaryLoading, setSummaryLoading] = useState(true);
  const [summaryError, setSummaryError] = useState(null);

  useEffect(() => {
    // Fetch dioceses data
    fetch('/api/dioceses')
      .then(response => {
        if (!response.ok) {
          throw new Error('Network response was not ok');
        }
        return response.json();
      })
      .then(data => {
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

    // Fetch summary data
    fetch('/api/summary')
      .then(response => {
        if (!response.ok) {
          throw new Error('Network response was not ok');
        }
        return response.json();
      })
      .then(data => {
        if (data.error) {
          throw new Error(data.error);
        }
        setSummary(data);
        setSummaryLoading(false);
      })
      .catch(error => {
        setSummaryError(error.message);
        setSummaryLoading(false);
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
        <h2>Data Summary</h2>
        {summaryLoading && <Spinner animation="border" />}
        {summaryError && <Alert variant="danger">Error fetching summary: {summaryError}</Alert>}
        {!summaryLoading && !summaryError && summary && (
          <Table striped bordered hover responsive className="mb-4">
            <thead>
              <tr>
                <th>Total Dioceses Processed</th>
                <th>Parish Directories Found</th>
                <th>Parish Directories Not Found</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td>{summary.total_dioceses_processed}</td>
                <td>{summary.found_parish_directories}</td>
                <td>{summary.not_found_parish_directories}</td>
              </tr>
            </tbody>
          </Table>
        )}

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

      <Container className="mt-4">
        <h2>Reports</h2>
        <div className="d-flex flex-wrap justify-content-around">
          <div className="p-2">
            <h3>Dioceses Records Over Time</h3>
            <img src="/dioceses_records_over_time.png" alt="Dioceses Records Over Time" className="img-fluid" />
          </div>
          <div className="p-2">
            <h3>Dioceses Parish Directory Records Over Time</h3>
            <img src="/diocesesparishdirectory_records_over_time.png" alt="Dioceses Parish Directory Records Over Time" className="img-fluid" />
          </div>
          <div className="p-2">
            <h3>Parishes Records Over Time</h3>
            <img src="/parishes_records_over_time.png" alt="Parishes Records Over Time" className="img-fluid" />
          </div>
          <div className="p-2">
            <h3>Parish Schedules Records Over Time</h3>
            <img src="/parishschedules_records_over_time.png" alt="Parish Schedules Records Over Time" className="img-fluid" />
          </div>
        </div>
      </Container>
    </>
  );
}

export default App;