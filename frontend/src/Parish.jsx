import React, { useState, useEffect } from 'react';
import { useLocation } from 'react-router-dom';
import { Container, Spinner, Alert, Card, Table, Badge } from 'react-bootstrap';

function Parish() {
  const { search } = useLocation();
  const queryParams = new URLSearchParams(search);
  const id = queryParams.get('id');

  const [parish, setParish] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchParishDetails = async () => {
      if (!id) {
        setError('Parish ID not provided.');
        setLoading(false);
        return;
      }
      setLoading(true);
      setError(null);
      try {
        const response = await fetch(`/api/parish?parish_id=${id}`);
        if (!response.ok) {
          throw new Error('Network response was not ok');
        }
        const result = await response.json();
        if (result.error) {
          throw new Error(result.error);
        }
        setParish(result.data);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    fetchParishDetails();
  }, [id]);

  if (loading) {
    return <Spinner animation="border" />;
  }

  if (error) {
    return <Alert variant="danger">Error fetching parish details: {error}</Alert>;
  }

  if (!parish) {
    return <Alert variant="info">No parish data found.</Alert>;
  }

  const formatFactType = (factType) => {
    return factType.replace(/([A-Z])/g, ' $1').replace(/^./, str => str.toUpperCase());
  };

  const parseScheduleData = (factValue) => {
    try {
      return JSON.parse(factValue);
    } catch (e) {
      return null;
    }
  };

  const formatAddress = (parish) => {
    // Try full_address first, then construct from parts
    if (parish.full_address) {
      return parish.full_address;
    }

    // Try the "Address" field (for compatibility)
    if (parish.Address) {
      return parish.Address;
    }

    // Construct from individual parts
    const parts = [];
    if (parish["Street Address"]) parts.push(parish["Street Address"]);
    if (parish.City) parts.push(parish.City);
    if (parish.State) parts.push(parish.State);
    if (parish["Zip Code"]) parts.push(parish["Zip Code"]);

    return parts.length > 0 ? parts.join(", ") : null;
  };

  const getWebsiteUrl = (parish) => {
    // Try both "Website" and "Web" fields
    return parish.Website || parish.Web;
  };

  return (
    <Container className="mt-4">
      <Card>
        <Card.Header as="h2">{parish.Name}</Card.Header>
        <Card.Body>
          {formatAddress(parish) && (
            <Card.Text>
              <strong>Address:</strong> {formatAddress(parish)}
            </Card.Text>
          )}
          {getWebsiteUrl(parish) && (
            <Card.Text>
              <strong>Website:</strong> <a href={getWebsiteUrl(parish)} target="_blank" rel="noopener noreferrer">{getWebsiteUrl(parish)}</a>
            </Card.Text>
          )}
          {parish.diocese_name && (
            <Card.Text>
              <strong>Diocese:</strong> {parish.diocese_name}
            </Card.Text>
          )}

          <h3>Schedule Information</h3>
          {parish.schedules && parish.schedules.length > 0 ? (
            <Table striped bordered hover responsive>
              <thead>
                <tr>
                  <th>Schedule Type</th>
                  <th>Details</th>
                  <th>Confidence</th>
                  <th>Source</th>
                </tr>
              </thead>
              <tbody>
                {parish.schedules.map((schedule, index) => {
                  const parsedData = parseScheduleData(schedule.fact_value);
                  return (
                    <tr key={schedule.id || index}>
                      <td>
                        <strong>{formatFactType(schedule.fact_type)}</strong>
                      </td>
                      <td>
                        <div>
                          <p>{schedule.fact_string}</p>
                          {parsedData && parsedData.days_offered && (
                            <div>
                              <small className="text-muted">
                                <strong>Days:</strong> {parsedData.days_offered.join(', ')}<br/>
                                {parsedData.times && <><strong>Times:</strong> {parsedData.times.join(', ')}<br/></>}
                                {parsedData.frequency && <><strong>Frequency:</strong> {parsedData.frequency}</>}
                              </small>
                            </div>
                          )}
                        </div>
                      </td>
                      <td>
                        <Badge bg={schedule.confidence_score >= 90 ? 'success' : schedule.confidence_score >= 70 ? 'warning' : 'secondary'}>
                          {schedule.confidence_score}%
                        </Badge>
                      </td>
                      <td>
                        <small>
                          <a href={schedule.fact_source_url} target="_blank" rel="noopener noreferrer">
                            {schedule.extraction_method}
                          </a>
                        </small>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </Table>
          ) : (
            <Alert variant="info">No schedule information available for this parish.</Alert>
          )}
        </Card.Body>
      </Card>
    </Container>
  );
}

export default Parish;