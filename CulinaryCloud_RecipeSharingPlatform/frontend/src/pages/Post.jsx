import { useNavigate } from "react-router-dom";

function Post({ recipe }) {
  const navigate = useNavigate();

  const handleStartCooking = () => {
    navigate("/home/start-cooking", { state: { recipe } });
  };

  return (
    <div className="post-info">
      <h3 className="post-heading">Ingredients</h3>
      <table className="post-table">
        <thead>
          <tr className="post-row">
            <th className="post-table-heading">Ingredient</th>
            <th className="post-table-heading">Quantity</th>
            <th className="post-table-heading">Unit</th>
          </tr>
        </thead>
        <tbody>
          {recipe.steps?.map((step, stepIndex) =>
            step.ingredients.map((ing, i) => (
              <tr key={`${stepIndex}-${i}`} className="post-row">
                <td className="post-table-data">{ing.name}</td>
                <td className="post-table-data">{ing.quantity}</td>
                <td className="post-table-data">{ing.unit}</td>
              </tr>
            ))
          )}
        </tbody>
      </table>

      <h3 className="post-cooking-heading">Cooking Process</h3>
      {recipe.steps?.map((step, index) => (
        <div key={index} className="cooking-step">
          <i className="fa-solid fa-thumbtack"></i>
          <p className="cooking-step"> <span className="cooking-step-heading"> Step {index + 1}: </span> {step.description}</p>
        </div>
      ))}

      <h3 className="post-cooking-heading">Nutritional Information</h3>
      {recipe.nutrition ? (
        <table className="post-table">
          <thead>
            <tr className="post-row">
              <th className="post-table-heading">Nutrient</th>
              <th className="post-table-heading">Amount</th>
            </tr>
          </thead>
          <tbody>
            <tr className="post-row">
              <td className="post-table-data">Calories</td>
              <td className="post-table-data">{recipe.nutrition.calories}</td>
            </tr>
            <tr className="post-row">
              <td className="post-table-data">Protein (g)</td>
              <td className="post-table-data">{recipe.nutrition.protein}</td>
            </tr>
            <tr className="post-row">
              <td className="post-table-data">Fat (g)</td>
              <td className="post-table-data">{recipe.nutrition.fat}</td>
            </tr>
            <tr className="post-row">
              <td className="post-table-data">Carbs (g)</td>
              <td className="post-table-data">{recipe.nutrition.carbs}</td>
            </tr>
          </tbody>
        </table>
      ) : (
        <p>No nutritional information available.</p>
      )}

      {recipe.videoUrls?.length > 0 && (
        <div className="video-section">
          <h3 className="post-cooking-heading">Video Guide</h3>
          {recipe.videoUrls.map((url, index) => (
            <video key={index} controls width="100%" style={{ marginBottom: "10px" }}>
              <source src={url} type="video/mp4" />
              Your browser does not support the video tag.
            </video>
          ))}
        </div>
      )}

      <div className="start-trial">
        <button className="start-cooking" onClick={handleStartCooking}>
          Start Cooking
        </button>
      </div>
    </div>
  );
}

export default Post;
