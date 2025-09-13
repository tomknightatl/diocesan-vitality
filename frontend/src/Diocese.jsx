import { useState, useEffect } from 'react';
import { useLocation } from 'react-router-dom';
import { Container, Table, Spinner, Alert, Card } from 'react-bootstrap';

function Diocese() {
  const { search } = useLocation();
  const queryParams = new URLSearchParams(search);
  const id = queryParams.get('id');

  const [diocese, setDiocese] = useState(null);
  const [parishes, setParishes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchDioceseDetails = async () => {
      if (!id) return; // Don't fetch if no id
      setLoading(true);
      setError(null);
      try {
        // Fetch diocese details
        const dioceseResponse = await fetch(`/api/dioceses/${id}`);
        if (!dioceseResponse.ok) {
          throw new Error('Network response was not ok');
        }
        const dioceseResult = await dioceseResponse.json();
        if (dioceseResult.error) {
          throw new Error(dioceseResult.error);
        }
        setDiocese(dioceseResult.data);

        // Fetch parishes
        const filter = queryParams.get('filter');
        const parishesResponse = await fetch(`/api/dioceses/${id}/parishes${filter ? `?filter=${filter}` : ''}`);
        if (!parishesResponse.ok) {
          throw new Error('Network response was not ok');
        }
        const parishesResult = await parishesResponse.json();
        if (parishesResult.error) {
          throw new Error(parishesResult.error);
        }
        setParishes(parishesResult.data);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    fetchDioceseDetails();
  }, [id, search]);

  if (loading) {
    return <Spinner animation="border" />;
  }

  if (error) {
    return <Alert variant="danger">Error fetching data: {error}</Alert>;
  }

  return (
    <Container className="mt-4">
      {diocese && (
        <Card className="mb-4">
          <Card.Header as="h2">{diocese.Name}</Card.Header>
          <Card.Body>
            <Card.Text>
              <strong>Address:</strong> {diocese.Address}
            </Card.Text>
            <Card.Text>
              <strong>Website:</strong> <a href={diocese.Website} target="_blank" rel="noopener noreferrer">{diocese.Website}</a>
            </Card.Text>
          </Card.Body>
        </Card>
      )}

      <h2>Parishes</h2>
      <Table striped bordered hover responsive>
        <thead>
          <tr>
            <th>Name</th>
            <th>Address</th>
            <th>Website</th>
            <th>Reconciliation</th>
            <th>Adoration</th>
          </tr>
        </thead>
        <tbody>
          {parishes.map((parish, index) => (
            <tr key={parish.id || index}>
              <td>{parish.Name}</td>
              <td>{parish['Street Address']}</td>
              <td><a href={parish.Web} target="_blank" rel="noopener noreferrer">{parish.Web}</a></td>
              <td>{parish.reconciliation_facts ? 'Yes' : 'No'}</td>
              <td>{parish.adoration_facts ? 'Yes' : 'No'}</td>
            </tr>
          ))}
        </tbody>
      </Table>
    </Container>
  );
}

export default Diocese;