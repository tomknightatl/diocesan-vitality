import { useState, useEffect } from 'react';
import { useLocation } from 'react-router-dom';
import { Container, Table, Spinner, Alert, Card } from 'react-bootstrap';
import ParishList from './ParishList';

function Diocese() {
  const { search } = useLocation();
  const queryParams = new URLSearchParams(search);
  const id = queryParams.get('id');

  const [diocese, setDiocese] = useState(null);
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

      <ParishList dioceseId={id} />
    </Container>
  );
}

export default Diocese;
