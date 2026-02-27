public class ServiceWithCallChain {

    private boolean isValidInput;

    // Entry method that calls validateInput() and processRequest()
    public String executeService(int amount, boolean priority) {
        validateInput(amount);
        if (isValidInput) {
            boolean approved = checkApproval(amount, priority);
            if (approved) {
                return "approved";
            } else {
                return "rejected";
            }
        } else {
            return "invalid";
        }
    }

    // Sets a field side-effect: this.isValidInput
    private void validateInput(int amount) {
        if (amount > 0 && amount < 1000000) {
            this.isValidInput = true;
        } else {
            this.isValidInput = false;
        }
    }

    // Returns a boolean value to the caller
    private boolean checkApproval(int amount, boolean priority) {
        if (priority) {
            return true;
        } else if (amount < 10000) {
            return true;
        } else {
            return false;
        }
    }
}
